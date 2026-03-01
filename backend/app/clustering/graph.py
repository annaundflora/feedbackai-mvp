"""ClusteringGraph -- LangGraph StateGraph fuer Clustering-Pipeline.

Implementiert TNT-LLM + GoalEx + Clio Hybrid:
- generate_taxonomy: Initiale Taxonomie aus allen Facts (mode=full)
- assign_facts: Facts zu Clustern zuordnen (incremental + full)
- validate_quality: Qualitaet der Zuordnungen pruefen
- refine_clusters: Korrektur bei Qualitaetsproblemen (max 3 Loops)
- generate_summaries: Cluster-Zusammenfassungen generieren
- check_suggestions: Merge/Split-Vorschlaege generieren

Folgt dem Pattern aus backend/app/interview/graph.py:
StateGraph(ClusteringState) + ChatOpenAI(base_url=openrouter)
"""
import json
import logging

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.clustering.graph_state import ClusteringState
from app.clustering.prompts import (
    ASSIGN_FACTS_PROMPT,
    CHECK_SUGGESTIONS_PROMPT,
    GENERATE_SUMMARIES_PROMPT,
    GENERATE_TAXONOMY_PROMPT,
    REFINE_CLUSTERS_PROMPT,
    VALIDATE_QUALITY_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_CORRECTION_ITERATIONS = 3
TAXONOMY_BATCH_SIZE = 20


class ClusteringGraph:
    """LangGraph StateGraph fuer Clustering-Pipeline.

    Implementiert TNT-LLM + GoalEx + Clio Hybrid:
    - generate_taxonomy: Initiale Taxonomie aus allen Facts (mode=full)
    - assign_facts: Facts zu Clustern zuordnen (incremental + full)
    - validate_quality: Qualitaet der Zuordnungen pruefen
    - refine_clusters: Korrektur bei Qualitaetsproblemen (max 3 Loops)
    - generate_summaries: Cluster-Zusammenfassungen generieren
    - check_suggestions: Merge/Split-Vorschlaege generieren

    Folgt dem Pattern aus backend/app/interview/graph.py:
    StateGraph(ClusteringState) + ChatOpenAI(base_url=openrouter)
    """

    def __init__(self, settings) -> None:
        self._settings = settings
        # LLM-Client fuer Clustering (model wird pro Node-Call aus State gelesen)
        self._llm_clustering = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.clustering_model_default,
            temperature=0.0,
        )
        # LLM-Client fuer Summary (leichteres Modell)
        self._llm_summary = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            model=settings.summary_model_default,
            temperature=0.0,
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Baut den StateGraph auf."""
        graph = StateGraph(ClusteringState)

        # Nodes registrieren
        graph.add_node("generate_taxonomy", self._node_generate_taxonomy)
        graph.add_node("assign_facts", self._node_assign_facts)
        graph.add_node("validate_quality", self._node_validate_quality)
        graph.add_node("refine_clusters", self._node_refine_clusters)
        graph.add_node("generate_summaries", self._node_generate_summaries)
        graph.add_node("check_suggestions", self._node_check_suggestions)

        # Entry-Point: mode-abhaengig
        graph.set_conditional_entry_point(
            lambda state: "generate_taxonomy" if state["mode"] == "full" else "assign_facts",
            {
                "generate_taxonomy": "generate_taxonomy",
                "assign_facts": "assign_facts",
            },
        )

        # Edges
        graph.add_edge("generate_taxonomy", "assign_facts")
        graph.add_edge("assign_facts", "validate_quality")
        graph.add_conditional_edges(
            "validate_quality",
            self._route_after_validation,
            {
                "refine": "refine_clusters",
                "ok": "generate_summaries",
            },
        )
        graph.add_edge("refine_clusters", "generate_summaries")
        graph.add_edge("generate_summaries", "check_suggestions")
        graph.add_edge("check_suggestions", END)

        return graph.compile()

    def _route_after_validation(self, state: ClusteringState) -> str:
        """Routing nach validate_quality: 'refine' oder 'ok'."""
        if state["quality_ok"] or state["iteration"] >= MAX_CORRECTION_ITERATIONS:
            return "ok"
        return "refine"

    def _get_llm_for_model(self, model: str, purpose: str = "clustering") -> ChatOpenAI:
        """Gibt den LLM-Client fuer ein bestimmtes Modell zurueck."""
        if purpose == "summary":
            # Summary-Modell verwenden wenn angegeben, sonst clustering-Modell
            base_llm = self._llm_summary
        else:
            base_llm = self._llm_clustering

        # Falls das gewuenschte Modell vom Default abweicht, neue Instanz erstellen
        if model and model != getattr(self._settings, "clustering_model_default" if purpose != "summary" else "summary_model_default", ""):
            return ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self._settings.openrouter_api_key,
                model=model,
                temperature=0.0,
            )
        return base_llm

    def _format_prompt_context_section(self, prompt_context: str | None) -> str:
        """Formatiert den optionalen prompt_context fuer Prompts."""
        if prompt_context:
            return f"\nAdditional Context: {prompt_context}\n"
        return ""

    def _format_facts_text(self, facts: list[dict]) -> str:
        """Formatiert Facts als lesbaren Text."""
        lines = []
        for i, fact in enumerate(facts, 1):
            lines.append(f"{i}. [ID: {fact.get('id', 'unknown')}] {fact.get('content', '')}")
        return "\n".join(lines)

    def _format_clusters_text(self, clusters: list[dict]) -> str:
        """Formatiert Cluster als lesbaren Text fuer Prompts."""
        lines = []
        for cluster in clusters:
            cluster_id = cluster.get("id")
            name = cluster.get("name", "")
            summary = cluster.get("summary", "")
            fact_count = cluster.get("fact_count", 0)
            if cluster_id:
                # Bestehender Cluster mit echter UUID
                if summary:
                    lines.append(f"- [id:{cluster_id}] {name}: {summary} ({fact_count} facts)")
                else:
                    lines.append(f"- [id:{cluster_id}] {name} ({fact_count} facts)")
            else:
                # Neuer Cluster (noch keine UUID) — LLM soll new_cluster_name verwenden
                if summary:
                    lines.append(f"- [NEW] {name}: {summary} ({fact_count} facts)")
                else:
                    lines.append(f"- [NEW] {name} ({fact_count} facts)")
        return "\n".join(lines)

    def _parse_json_response(self, content: str, expected_type: type) -> list | dict:
        """Parst JSON-Response vom LLM mit Fallback."""
        if isinstance(content, list):
            content = "".join(str(c) for c in content)

        # Versuche direktes JSON-Parsing
        try:
            parsed = json.loads(content)
            if isinstance(parsed, expected_type):
                return parsed
        except json.JSONDecodeError:
            pass

        # Versuche JSON aus Markdown-Codeblock zu extrahieren
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
                if isinstance(parsed, expected_type):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Versuche JSON-Array/-Objekt direkt zu finden
        if expected_type == list:
            array_match = re.search(r"\[[\s\S]*\]", content)
            if array_match:
                try:
                    parsed = json.loads(array_match.group(0))
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return []
        else:
            obj_match = re.search(r"\{[\s\S]*\}", content)
            if obj_match:
                try:
                    parsed = json.loads(obj_match.group(0))
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return {}

    async def _node_generate_taxonomy(self, state: ClusteringState) -> dict:
        """Node: Initiale Taxonomie aus allen Facts generieren (mode=full).

        TNT-LLM Pattern: Mini-Batches (20 Facts/Batch) -> LLM generiert
        Cluster-Namen -> deduplizieren -> initiale Taxonomie.

        Input:  state["facts"] -- alle Facts des Projekts
        Output: state["existing_clusters"] = [{id: None, name: "...", summary: None}]
        """
        logger.info(f"[generate_taxonomy] Processing {len(state['facts'])} facts for project {state['project_id']}")

        facts = state["facts"]
        research_goal = state["research_goal"]
        prompt_context = state.get("prompt_context")
        model = state.get("model_clustering") or getattr(self._settings, "clustering_model_default", "")
        batch_size = getattr(self._settings, "clustering_taxonomy_batch_size", TAXONOMY_BATCH_SIZE)

        llm = self._get_llm_for_model(model, purpose="clustering")
        prompt_context_section = self._format_prompt_context_section(prompt_context)

        # Mini-Batches verarbeiten
        all_cluster_names: list[str] = []
        batches = [facts[i:i + batch_size] for i in range(0, len(facts), batch_size)]
        total_batches = len(batches)
        logger.debug(
            f"[generate_taxonomy] project={state['project_id']} | "
            f"facts={len(facts)} | batch_size={batch_size} | total_batches={total_batches}"
        )

        for batch_idx, batch in enumerate(batches, 1):
            facts_text = self._format_facts_text(batch)
            existing_taxonomy = "\n".join(f"- {name}" for name in all_cluster_names) or "None yet"

            prompt = GENERATE_TAXONOMY_PROMPT.format(
                research_goal=research_goal,
                prompt_context_section=prompt_context_section,
                batch_number=batch_idx,
                total_batches=total_batches,
                facts_text=facts_text,
                existing_taxonomy=existing_taxonomy,
            )

            try:
                response = await llm.ainvoke(prompt)
                content = response.content
                new_names = self._parse_json_response(content, list)

                # Nur Strings, deduplizieren
                for name in new_names:
                    if isinstance(name, str) and name and name not in all_cluster_names:
                        all_cluster_names.append(name)
            except Exception as e:
                logger.warning(f"[generate_taxonomy] Batch {batch_idx} failed: {e}")
                continue

        # Initiale Cluster-Liste erstellen (ohne echte IDs — werden in service.py angelegt)
        initial_clusters = [
            {"id": None, "name": name, "summary": None, "fact_count": 0}
            for name in all_cluster_names
        ]

        logger.info(f"[generate_taxonomy] Generated {len(initial_clusters)} initial cluster names")
        return {"existing_clusters": initial_clusters}

    async def _node_assign_facts(self, state: ClusteringState) -> dict:
        """Node: Facts zu Clustern zuordnen (GoalEx Pattern).

        LLM sieht: facts + existing_clusters + research_goal + prompt_context
        LLM Output: assignments (fact_id -> cluster_id oder new_cluster_name)

        Input:  state["facts"], state["existing_clusters"], state["research_goal"]
        Output: state["assignments"], state["new_clusters"]
        """
        logger.info(f"[assign_facts] Assigning {len(state['facts'])} facts to {len(state['existing_clusters'])} clusters")

        facts = state["facts"]
        existing_clusters = state["existing_clusters"]
        research_goal = state["research_goal"]
        prompt_context = state.get("prompt_context")
        model = state.get("model_clustering") or getattr(self._settings, "clustering_model_default", "")

        llm = self._get_llm_for_model(model, purpose="clustering")
        prompt_context_section = self._format_prompt_context_section(prompt_context)

        clusters_text = self._format_clusters_text(existing_clusters)
        facts_text = self._format_facts_text(facts)

        prompt = ASSIGN_FACTS_PROMPT.format(
            research_goal=research_goal,
            prompt_context_section=prompt_context_section,
            clusters_text=clusters_text,
            facts_text=facts_text,
        )

        assignments: list[dict] = []
        new_cluster_names: list[str] = []

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            logger.debug(
                f"[assign_facts] LLM raw response (first 1000 chars): "
                f"{str(content)[:1000]}"
            )
            raw_assignments = self._parse_json_response(content, list)
            logger.debug(f"[assign_facts] parsed {len(raw_assignments)} raw assignments from LLM")

            for assignment in raw_assignments:
                if not isinstance(assignment, dict):
                    continue
                fact_id = assignment.get("fact_id")
                cluster_id = assignment.get("cluster_id")
                new_cluster_name = assignment.get("new_cluster_name")

                if not fact_id:
                    continue

                assignments.append({
                    "fact_id": fact_id,
                    "cluster_id": cluster_id,
                    "new_cluster_name": new_cluster_name,
                })

                if new_cluster_name and new_cluster_name not in new_cluster_names:
                    new_cluster_names.append(new_cluster_name)

        except Exception as e:
            logger.error(f"[assign_facts] LLM call failed: {e}")
            # Fallback: alle Facts ohne Cluster-Zuordnung
            assignments = [
                {"fact_id": f.get("id"), "cluster_id": None, "new_cluster_name": None}
                for f in facts
                if f.get("id")
            ]

        # Neue Cluster aus Assignments ableiten
        new_clusters: list[dict] = []
        for cluster_name in new_cluster_names:
            fact_ids = [
                a["fact_id"] for a in assignments
                if a.get("new_cluster_name") == cluster_name and a.get("fact_id")
            ]
            new_clusters.append({"name": cluster_name, "fact_ids": fact_ids})

        # Assignments aufschlüsseln für Debug
        n_to_existing = sum(1 for a in assignments if a.get("cluster_id") and not a.get("new_cluster_name"))
        n_to_new = sum(1 for a in assignments if a.get("new_cluster_name"))
        n_unassigned = sum(1 for a in assignments if not a.get("cluster_id") and not a.get("new_cluster_name"))
        logger.info(
            f"[assign_facts] Generated {len(assignments)} assignments | "
            f"to_existing_cluster={n_to_existing} | to_new_cluster={n_to_new} | unassigned={n_unassigned} | "
            f"new_cluster_names={new_cluster_names}"
        )
        logger.debug(f"[assign_facts] {len(new_clusters)} new clusters: {[nc['name'] for nc in new_clusters]}")
        return {
            "assignments": assignments,
            "new_clusters": new_clusters,
        }

    async def _node_validate_quality(self, state: ClusteringState) -> dict:
        """Node: Qualitaet der Zuordnungen validieren.

        LLM prueft: Kohaerenz der Cluster, Groessen-Balance, Themen-Ueberlappung.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["quality_ok"] (bool), state["iteration"] += 1
        """
        logger.info(f"[validate_quality] Iteration {state.get('iteration', 0) + 1}")

        assignments = state.get("assignments", [])
        existing_clusters = state.get("existing_clusters", [])
        new_clusters = state.get("new_clusters", [])
        research_goal = state["research_goal"]
        model = state.get("model_clustering") or getattr(self._settings, "clustering_model_default", "")

        llm = self._get_llm_for_model(model, purpose="clustering")

        # Cluster-Summary-Text aufbauen
        cluster_summary_lines = []
        all_clusters = list(existing_clusters) + [
            {"id": f"new:{nc['name']}", "name": nc["name"], "summary": None}
            for nc in new_clusters
        ]

        for cluster in all_clusters:
            cluster_id = cluster.get("id") or f"new:{cluster.get('name', '')}"
            cluster_name = cluster.get("name", "")
            cluster_facts = [
                a for a in assignments
                if a.get("cluster_id") == cluster_id or a.get("new_cluster_name") == cluster_name
            ]
            cluster_summary_lines.append(
                f"Cluster '{cluster_name}' (id={cluster_id}): {len(cluster_facts)} facts"
            )

        cluster_summary_text = "\n".join(cluster_summary_lines)

        prompt = VALIDATE_QUALITY_PROMPT.format(
            research_goal=research_goal,
            cluster_summary_text=cluster_summary_text,
        )

        quality_ok = True
        issues: list[str] = []

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            result = self._parse_json_response(content, dict)

            if isinstance(result, dict):
                quality_ok = bool(result.get("quality_ok", True))
                issues = result.get("issues", [])
        except Exception as e:
            logger.warning(f"[validate_quality] LLM call failed: {e}, defaulting to quality_ok=True")
            quality_ok = True

        current_iteration = state.get("iteration", 0) + 1
        logger.info(f"[validate_quality] quality_ok={quality_ok}, issues={len(issues)}, iteration={current_iteration}")

        return {
            "quality_ok": quality_ok,
            "iteration": current_iteration,
        }

    async def _node_refine_clusters(self, state: ClusteringState) -> dict:
        """Node: Zuordnungen korrigieren (Self-Correction Loop).

        LLM korrigiert Zuordnungen basierend auf Qualitaets-Issues.
        Wird max MAX_CORRECTION_ITERATIONS mal ausgefuehrt.

        Input:  state["assignments"], state["new_clusters"] (mit Issues-Kontext)
        Output: state["assignments"] (korrigiert), state["new_clusters"] (korrigiert)
        """
        logger.info(f"[refine_clusters] Refining after iteration {state.get('iteration', 0)}")

        assignments = state.get("assignments", [])
        existing_clusters = state.get("existing_clusters", [])
        new_clusters = state.get("new_clusters", [])
        research_goal = state["research_goal"]
        model = state.get("model_clustering") or getattr(self._settings, "clustering_model_default", "")

        llm = self._get_llm_for_model(model, purpose="clustering")

        # Cluster-Summary-Text aufbauen
        all_clusters = list(existing_clusters) + [
            {"id": f"new:{nc['name']}", "name": nc["name"], "summary": None}
            for nc in new_clusters
        ]
        cluster_summary_lines = []
        for cluster in all_clusters:
            cluster_id = cluster.get("id") or f"new:{cluster.get('name', '')}"
            cluster_name = cluster.get("name", "")
            cluster_facts = [
                a for a in assignments
                if a.get("cluster_id") == cluster_id or a.get("new_cluster_name") == cluster_name
            ]
            fact_contents = []
            for a in cluster_facts[:5]:  # Nur erste 5 Facts anzeigen
                cluster_summary_lines.append(
                    f"Cluster '{cluster_name}' (id={cluster_id}): {len(cluster_facts)} facts"
                )
                break

        cluster_summary_text = "\n".join(cluster_summary_lines) if cluster_summary_lines else "No cluster assignments yet"

        prompt = REFINE_CLUSTERS_PROMPT.format(
            research_goal=research_goal,
            issues_text="Quality issues detected in previous iteration",
            cluster_summary_text=cluster_summary_text,
        )

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            corrections = self._parse_json_response(content, list)

            if corrections:
                # Korrekturen in assignments einpflegen
                correction_map = {c["fact_id"]: c for c in corrections if isinstance(c, dict) and c.get("fact_id")}

                updated_assignments = []
                for assignment in assignments:
                    fact_id = assignment.get("fact_id")
                    if fact_id and fact_id in correction_map:
                        correction = correction_map[fact_id]
                        updated_assignments.append({
                            "fact_id": fact_id,
                            "cluster_id": correction.get("cluster_id"),
                            "new_cluster_name": correction.get("new_cluster_name"),
                        })
                    else:
                        updated_assignments.append(assignment)

                # Neue Cluster aus Korrekturen ableiten
                new_cluster_names_from_corrections = set()
                for correction in corrections:
                    new_name = correction.get("new_cluster_name") if isinstance(correction, dict) else None
                    if new_name:
                        new_cluster_names_from_corrections.add(new_name)

                # Bestehende neue Cluster beibehalten + neue hinzufuegen
                existing_new_names = {nc["name"] for nc in new_clusters}
                for cluster_name in new_cluster_names_from_corrections:
                    if cluster_name not in existing_new_names:
                        fact_ids = [
                            a["fact_id"] for a in updated_assignments
                            if a.get("new_cluster_name") == cluster_name
                        ]
                        new_clusters = new_clusters + [{"name": cluster_name, "fact_ids": fact_ids}]

                logger.info(f"[refine_clusters] Applied {len(correction_map)} corrections")
                return {
                    "assignments": updated_assignments,
                    "new_clusters": new_clusters,
                }

        except Exception as e:
            logger.warning(f"[refine_clusters] LLM call failed: {e}, keeping existing assignments")

        return {}  # Keine Aenderungen

    async def _node_generate_summaries(self, state: ClusteringState) -> dict:
        """Node: Cluster-Zusammenfassungen generieren.

        Leichteres Modell (model_summary) pro Cluster.
        Sammelt alle Facts eines Clusters -> LLM generiert Zusammenfassung.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["summaries"] = {cluster_id_or_name: summary_text}
        """
        logger.info("[generate_summaries] Generating cluster summaries")

        assignments = state.get("assignments", [])
        existing_clusters = state.get("existing_clusters", [])
        new_clusters = state.get("new_clusters", [])
        research_goal = state["research_goal"]
        model_summary = state.get("model_summary") or getattr(self._settings, "summary_model_default", "")
        facts = state.get("facts", [])

        llm = self._get_llm_for_model(model_summary, purpose="summary")

        # Facts per cluster_id mappen
        facts_by_id = {f.get("id"): f for f in facts if f.get("id")}

        summaries: dict[str, str] = {}

        # Bestehende Cluster (mit echter UUID)
        for cluster in existing_clusters:
            cluster_id = cluster.get("id")
            cluster_name = cluster.get("name", "")
            if not cluster_id or not cluster_name:
                continue

            # Facts dieses Clusters sammeln
            cluster_fact_ids = [
                a["fact_id"] for a in assignments
                if a.get("cluster_id") == cluster_id
            ]
            cluster_facts = [facts_by_id[fid] for fid in cluster_fact_ids if fid in facts_by_id]

            if not cluster_facts:
                continue

            facts_text = self._format_facts_text(cluster_facts)
            prompt = GENERATE_SUMMARIES_PROMPT.format(
                research_goal=research_goal,
                cluster_name=cluster_name,
                facts_text=facts_text,
            )

            try:
                response = await llm.ainvoke(prompt)
                content = response.content
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)
                summaries[str(cluster_id)] = content.strip()
            except Exception as e:
                logger.warning(f"[generate_summaries] Failed for cluster {cluster_id}: {e}")

        # Neue Cluster (ohne echte UUID, Key = name)
        for new_cluster in new_clusters:
            cluster_name = new_cluster.get("name", "")
            if not cluster_name:
                continue

            # Facts dieses neuen Clusters sammeln
            cluster_fact_ids = [
                a["fact_id"] for a in assignments
                if a.get("new_cluster_name") == cluster_name
            ]
            cluster_facts = [facts_by_id[fid] for fid in cluster_fact_ids if fid in facts_by_id]

            if not cluster_facts:
                continue

            facts_text = self._format_facts_text(cluster_facts)
            prompt = GENERATE_SUMMARIES_PROMPT.format(
                research_goal=research_goal,
                cluster_name=cluster_name,
                facts_text=facts_text,
            )

            try:
                response = await llm.ainvoke(prompt)
                content = response.content
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)
                summaries[cluster_name] = content.strip()
            except Exception as e:
                logger.warning(f"[generate_summaries] Failed for new cluster '{cluster_name}': {e}")

        logger.info(f"[generate_summaries] Generated {len(summaries)} summaries")
        return {"summaries": summaries}

    async def _node_check_suggestions(self, state: ClusteringState) -> dict:
        """Node: Merge/Split-Vorschlaege generieren.

        Merge-Vorschlaege: LLM prueft Aehnlichkeit der Cluster (>80% -> Vorschlag).
        Split-Vorschlaege: Cluster mit >8 Facts -> LLM prueft auf Sub-Themen.

        Input:  state["assignments"], state["existing_clusters"], state["new_clusters"]
        Output: state["suggestions"]
        """
        logger.info("[check_suggestions] Checking for merge/split suggestions")

        assignments = state.get("assignments", [])
        existing_clusters = state.get("existing_clusters", [])
        new_clusters = state.get("new_clusters", [])
        research_goal = state["research_goal"]
        model = state.get("model_clustering") or getattr(self._settings, "clustering_model_default", "")
        split_threshold = getattr(self._settings, "clustering_split_threshold", 8)

        llm = self._get_llm_for_model(model, purpose="clustering")

        # Alle Cluster (nur solche mit echter ID fuer Suggestions relevant)
        all_clusters_with_ids = [
            c for c in existing_clusters if c.get("id")
        ]

        if not all_clusters_with_ids:
            return {"suggestions": []}

        # Fact-Count per Cluster berechnen
        clusters_with_counts = []
        for cluster in all_clusters_with_ids:
            cluster_id = cluster.get("id")
            fact_count = len([a for a in assignments if a.get("cluster_id") == cluster_id])
            clusters_with_counts.append({
                **cluster,
                "fact_count": fact_count,
            })

        clusters_text = self._format_clusters_text(clusters_with_counts)

        prompt = CHECK_SUGGESTIONS_PROMPT.format(
            research_goal=research_goal,
            clusters_text=clusters_text,
            split_threshold=split_threshold,
        )

        suggestions: list[dict] = []

        try:
            response = await llm.ainvoke(prompt)
            content = response.content
            raw_suggestions = self._parse_json_response(content, list)

            for sug in raw_suggestions:
                if not isinstance(sug, dict):
                    continue
                sug_type = sug.get("type")
                if sug_type not in ("merge", "split"):
                    continue

                suggestion = {
                    "type": sug_type,
                    "source_cluster_id": sug.get("source_cluster_id"),
                }

                if sug_type == "merge":
                    suggestion["target_cluster_id"] = sug.get("target_cluster_id")
                    suggestion["similarity_score"] = sug.get("similarity_score")
                elif sug_type == "split":
                    suggestion["proposed_data"] = sug.get("proposed_subclusters", [])

                if suggestion.get("source_cluster_id"):
                    suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"[check_suggestions] LLM call failed: {e}")

        logger.info(f"[check_suggestions] Generated {len(suggestions)} suggestions")
        return {"suggestions": suggestions}

    async def invoke(self, initial_state: ClusteringState) -> ClusteringState:
        """Fuehrt den Clustering-Graph aus.

        Args:
            initial_state: Initialzustand mit project_id, facts, research_goal, mode etc.

        Returns:
            Finaler State nach Graph-Ausfuehrung (assignments, summaries, suggestions).
        """
        return await self._graph.ainvoke(initial_state)
