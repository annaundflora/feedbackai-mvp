# Research: LLM-Based Text Clustering (ohne Embeddings/HDBSCAN)

**Feature:** LLM Interview Clustering
**Datum:** 2026-02-28
**Zweck:** State-of-the-Art Research fuer Clustering-Architektur-Entscheidung

---

## Executive Summary

Pure LLM-basiertes Clustering (ohne Vektoren, ohne HDBSCAN) ist 2025/2026 ein aktiver Forschungsbereich mit mehreren produktionsreifen Ansaetzen. Der staerkste Kandidat fuer unser Use-Case (Interview-Feedback Clustering) ist eine **Kombination aus TNT-LLM (Microsoft) und Anthropic Clio Patterns**, implementiert als **LangGraph StateGraph mit Self-Correction Loop**.

**Empfohlener Ansatz:** "Text Clustering as Classification" — LLM generiert Taxonomie iterativ, dann klassifiziert LLM jedes Interview/Fact gegen diese Taxonomie. Inkrementell erweiterbar.

---

## 1. Akademische Referenz-Papers

### 1.1 TNT-LLM (Microsoft, KDD 2024)

**Paper:** [TnT-LLM: Text Mining at Scale with Large Language Models](https://arxiv.org/abs/2403.12173)
**Code:** [LangGraph Official Tutorial](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/tnt-llm/tnt-llm.ipynb)

**Architektur — 2-Phasen-Framework:**

```
Phase 1: Taxonomie-Generierung
  Dokumente → Summarize → Mini-Batches → LLM generiert Taxonomie
                                           → LLM verfeinert iterativ
                                           → LLM reviewed Ergebnis

Phase 2: Text-Klassifikation
  Taxonomie + Neue Dokumente → LLM klassifiziert → Labels zugewiesen
```

**Kern-Idee:**
- LLM liest Dokumente in Mini-Batches (Context-Window-kompatibel)
- Generiert Taxonomie iterativ (Batch 1 → initiale Taxonomie, Batch 2 → verfeinert, ...)
- Tiered LLM: GPT-4 fuer Taxonomie-Generierung, GPT-3.5 fuer Summarization
- Finale Klassifikation optional durch leichtgewichtigen Classifier (Logistic Regression)

**LangGraph StateGraph Code-Pattern:**

```python
from langgraph.graph import StateGraph

class TaxonomyGenerationState(TypedDict):
    documents: list[str]
    summaries: list[str]
    minibatch_indices: list[list[int]]
    current_batch: int
    taxonomy: str  # LLM-generierte Taxonomie als Text

graph = StateGraph(TaxonomyGenerationState)
graph.add_node("summarize", map_reduce_chain)
graph.add_node("get_minibatches", get_minibatches)
graph.add_node("generate_taxonomy", generate_taxonomy)
graph.add_node("update_taxonomy", update_taxonomy)
graph.add_node("review_taxonomy", review_taxonomy)

graph.add_edge("summarize", "get_minibatches")
graph.add_edge("get_minibatches", "generate_taxonomy")
graph.add_edge("generate_taxonomy", "update_taxonomy")
# Conditional: iterate until all batches processed
graph.add_conditional_edges("update_taxonomy", check_batches,
    {"continue": "update_taxonomy", "done": "review_taxonomy"})
```

**Relevanz fuer uns:** Direktes Vorbild. Unser LangGraph Interview-Graph Pattern kann wiederverwendet werden. Mini-Batch-Ansatz skaliert auf 100+ Interviews.

---

### 1.2 Text Clustering as Classification (SIGIR-AP 2025)

**Paper:** [Text Clustering as Classification with LLMs](https://arxiv.org/html/2410.00927v1)
**Code:** [github.com/ECNU-Text-Computing/Text-Clustering-via-LLM](https://github.com/ECNU-Text-Computing/Text-Clustering-via-LLM)

**Architektur — 2-Stufen ohne Embeddings:**

```
Stufe 1: Label-Generierung
  Dokumente (Mini-Batches) → LLM: "Generate labels" → Kandidaten-Labels
  Kandidaten-Labels → LLM: "Merge similar labels" → Finale Label-Liste

Stufe 2: Label-Zuweisung (= Klassifikation)
  Finale Labels + Dokument → LLM: "Classify into one label" → Zuordnung
  Falls kein Label passt → LLM generiert neues Label
```

**Prompt-Templates:**

```
# Label Generation
"Generate a label name based on the sentences: {batch_of_texts}"

# Label Merging
"Analyze the provided list of labels to identify entries that are
similar or duplicate, considering synonyms, variations in phrasing,
and closely related terms that essentially refer to the same concept."

# Label Assignment
"Categorize the sentence into one of the labels: {label_list}
Sentence: {text}
If the sentence does not match any label, generate a meaningful new label.
Please respond in JSON format."
```

**Ergebnisse:** Vergleichbar oder besser als Embedding-basierte Ansaetze, +12% bei manchen Datasets. Signifikant weniger Compute-Aufwand.

**Relevanz fuer uns:** Einfachster Ansatz. Kann direkt als "Fact Assignment" Schritt verwendet werden. JSON-Output-Format passt zu unserem API-Design.

---

### 1.3 GoalEx: Goal-Driven Explainable Clustering (EMNLP 2023)

**Paper:** [Goal-Driven Explainable Clustering via Language Descriptions](https://arxiv.org/abs/2305.13749)
**Code:** [github.com/ZihanWangKi/GoalEx](https://github.com/ZihanWangKi/GoalEx)

**Architektur — Propose-Assign-Select (PAS):**

```
1. PROPOSE: LLM + [corpus subset] + [goal]
   → "Brainstorm a list of explanations each representing a cluster"
   → Kandidaten-Cluster mit natuerlichsprachlichen Beschreibungen

2. ASSIGN: Fuer jedes Dokument:
   → "Does this document belong to cluster [description]?"
   → Zuordnung basierend auf Erklaerungen

3. SELECT: Integer Linear Programming
   → Optimale Cluster-Subset auswaehlen
   → Maximale Abdeckung, minimale Ueberlappung
```

**Kern-Innovation:** Goal-Driven! User gibt ein Ziel vor (z.B. "Cluster customer feedback by reason for dissatisfaction") und das LLM clustert entsprechend.

**Relevanz fuer uns:** HOCH. Unser `research_goal` pro Projekt ist exakt dieses Pattern. User definiert das Research-Ziel, LLM clustert zielgerichtet. Beispiel: "Clustere nach Schmerzpunkten beim Umzug" statt generischem Clustering.

---

### 1.4 k-LLMmeans: Summary-als-Zentroid (2025)

**Paper:** [k-LLMmeans: Scalable, Stable, and Interpretable Text Clustering via LLM-based Centroids](https://arxiv.org/abs/2502.09667)

**Architektur — Streaming-Native:**

```
Mini-Batch Variante:
  Batch 1 → k-means mit Embedding-Centroiden → LLM summarisiert Cluster
  Batch 2 → Zuordnung zu bestehenden Centroiden → LLM re-summarisiert
  Batch N → ...inkrementell weiter

Centroide = LLM-generierte Zusammenfassungen (nicht Vektoren!)
```

**Key Metrics:**
- 205.943 Posts mit nur 3.850 LLM-Calls geclustert
- LLM-Kosten skalieren NICHT mit Dataset-Groesse
- Mini-Batch-Variante fuer Streaming geeignet

**Relevanz fuer uns:** Bestaetigt dass inkrementelles Clustering mit LLM-Summaries als Cluster-Repraesentation funktioniert. Unser Cluster-Summary ist der "Centroid".

---

### 1.5 ClusterLLM: LLM als Guide (EMNLP 2023)

**Paper:** [ClusterLLM: Large Language Models as a Guide for Text Clustering](https://arxiv.org/abs/2305.14871)
**Code:** [github.com/zhang-yu-wei/ClusterLLM](https://github.com/zhang-yu-wei/ClusterLLM)

Nutzt LLM als "Triplet Oracle" — befragt LLM zu schwierigen Faellen ("Ist A naeher an B oder C?"). Benoetigt Embeddings als Basis, daher nur teilweise relevant.

---

### 1.6 Large Language Models Enable Few-Shot Clustering (MIT Press / TACL)

**Paper:** [Few-Shot Clustering](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00648/120476)

**3 Integrationsebenen fuer LLMs in Clustering:**

| Ebene | Wann | Was | Beispiel |
|-------|------|-----|----------|
| **Pre-Clustering** | Input verbessern | LLM reichert Dokumente an | Summary + Keywords extrahieren |
| **During Clustering** | Constraints liefern | LLM als Pairwise-Oracle | "Gehoeren A und B zusammen?" |
| **Post-Clustering** | Korrektur | LLM korrigiert Low-Confidence Zuordnungen | Self-Correction Loop |

**Relevanz fuer uns:** Unser Self-Correction Loop ist das "Post-Clustering" Pattern. LLM validiert Zuordnungen und korrigiert Fehler.

---

## 2. Industry-Implementierungen

### 2.1 Anthropic Clio (Dezember 2024)

**Paper:** [Clio: Privacy-Preserving Insights into Real-World AI Use](https://arxiv.org/html/2412.13678v1)
**Open Source:** [github.com/Phylliida/OpenClio](https://github.com/Phylliida/OpenClio)

**Architektur — 4-Stufen Pipeline:**

```
1. FACET EXTRACTION
   Conversation → Claude: "What is the user's overall request?"
                → Claude: "What task is the model performing?"
                → Claude: "What language?"
   → Structured Facets per Conversation

2. SEMANTIC CLUSTERING
   Facets → Gruppierung nach Aehnlichkeit
   → Cluster von Conversations

3. CLUSTER DESCRIPTION
   Cluster → Claude: "Summarize this cluster, exclude PII"
   → Cluster-Name + Summary

4. HIERARCHY BUILDING
   Flat Clusters → Multi-Level Hierarchie
   → Interactive Tree View
```

**Key Design Decisions:**
- Facets sind konfigurierbar (verschiedene "Linsen" auf dieselben Daten)
- Minimum-Cluster-Groesse enforced (Privacy: zu kleine Cluster werden verworfen)
- Claude macht ALLES (Extraction, Clustering, Description, Review)
- 94% Accuracy bei 20.000 synthetischen Conversations

**OpenClio Prompt-Beispiel (Facet Extraction):**

```python
# Request Facet
{
    "question": "What is the user's overall request for the assistant?",
    "prefill": "The user's overall request for the assistant is to",
    "summaryCriteria": "should be a clear single sentence that captures
                        the specific action or task"
}

# Task Facet
{
    "question": "What task is the model being asked to perform?",
    "summaryCriteria": "should be a clear single sentence that captures
                        the specific action or task the model is being
                        asked to perform"
}
```

**Relevanz fuer uns:** SEHR HOCH. Clio's Facet-Extraction ist unser Fact-Extraction. Clio's Clustering+Description ist unser Cluster-Pipeline. Clio beweist, dass pure LLM-basiertes Clustering in Produktion funktioniert (Millionen Conversations).

### 2.2 Anthropic Interviewer (Dezember 2025)

**Source:** [Anthropic Interviewer](https://www.anthropic.com/research/clio)

Anthropic selbst hat ein Claude-powered Qualitative-Research-Tool gebaut:
- Plant Fragen, fuehrt 10-15 Min Gespraeche, clustert Themen fuer menschliche Analysten
- 1.250 Professionals interviewt, Themen automatisch geclustert
- Zeigt: Interview → Clustering Pipeline ist ein validierter Workflow bei Anthropic

---

### 2.3 LLM-Based vs Traditional Clustering (Chris Ellis, Practitioner Blog)

**Source:** [chrisellis.dev](https://www.chrisellis.dev/articles/comparing-llm-based-vs-traditional-clustering-for-support-conversations)

**Vergleich:**

| Aspekt | Traditional (k-means/DBSCAN) | LLM-Based |
|--------|------------------------------|-----------|
| Geschwindigkeit | Schnell | Langsamer (API-Calls) |
| Skalierbarkeit | Hoch | Begrenzt durch API-Kosten |
| Semantische Qualitaet | Literal (Wort-Aehnlichkeit) | Nuanciert (Bedeutungs-Aehnlichkeit) |
| Erklaerbarkeit | Cluster = Vektoren (opak) | Cluster = Text-Labels (transparent) |
| Voice of Customer | Oberflaechlich | Tief (versteht Intent) |

**Fazit:** "LLM-basierte Clustering-Ansaetze uebertreffen klassische Algorithmen bei semantischer Kohaerenz, besonders fuer komplexe, nuancierte Gespraechsdaten."

---

### 2.4 Embedding vs Prompting (Side-by-Side Demo)

**Code:** [github.com/intellectronica/text-clustering-embedding-vs-prompting](https://github.com/intellectronica/text-clustering-embedding-vs-prompting)

Direkter Vergleich: Embedding+k-means vs. reines LLM-Prompting. LLM-Prompting liefert zusaetzlich Cluster-Beschreibungen und erfordert kein Embedding-Modell.

---

### 2.5 Microsoft ISE: Customer Feedback Insights via LLM

**Source:** [Microsoft ISE Developer Blog](https://devblogs.microsoft.com/ise/insights_generation_from_customer_feedback_using_llms/)

Produktions-Case fuer LLM-basierte Feedback-Analyse. Nutzt Prompt Engineering fuer Themen-Extraktion, Sentiment-Analyse und Wettbewerber-Vergleiche. Iteratives Prompt-Refinement fuer optimale Ergebnisse.

---

## 3. Konkrete Clustering-Patterns (fuer unsere Implementierung)

### Pattern 1: "Extract-Cluster-Validate" (EMPFOHLEN)

```
                    +---------+
                    | START   |
                    +----+----+
                         |
                         v
              +----------+----------+
              | 1. FACT EXTRACTION  |  LLM: Summary → atomare Facts
              | (pro Interview)     |  Output: [{fact, quote, interview_id}]
              +----------+----------+
                         |
                         v
              +----------+----------+
              | 2. TAXONOMY CHECK   |  Existieren Cluster?
              +----------+----------+
                    |           |
                 Nein          Ja
                    |           |
                    v           v
           +-------+--+  +----+--------+
           | 2a. INIT |  | 2b. ASSIGN  |
           | TAXONOMY |  | Facts zu    |
           | LLM gene-|  | bestehenden |
           | riert     |  | Clustern    |
           | initiale  |  | + ggf. neue |
           | Cluster   |  | vorschlagen |
           +---------+-+  +----+--------+
                    |           |
                    +-----+-----+
                          |
                          v
              +-----------+---------+
              | 3. SELF-CORRECTION  |  LLM validiert:
              | (max 3 Loops)       |  - Kohaerenz OK?
              +-----------+---------+  - Merge noetig?
                    |           |      - Split noetig?
                 OK          Issues
                    |           |
                    |     +-----+-------+
                    |     | 3a. REFINE  |
                    |     | LLM korri-  |
                    |     | giert       |----+
                    |     +-------------+    |
                    |           ^             |
                    |           +-------------+
                    v                (max 3x)
              +-----+-----------+
              | 4. SUMMARIZE    |  LLM generiert/aktualisiert
              | Cluster-Summaries|  Cluster-Zusammenfassungen
              +-----+-----------+
                    |
                    v
              +-----+-----------+
              | 5. PERSIST      |  Facts + Cluster in DB
              | + NOTIFY (SSE)  |  Dashboard Live-Update
              +-----------------+
```

### Pattern 2: Inkrementelles Clustering (Streaming)

```
Neues Interview abgeschlossen
         |
         v
[Fact Extraction] → Neue Facts
         |
         v
[LLM: "Given these existing clusters and their summaries,
       assign each new fact to the best cluster.
       If no cluster fits, propose a new cluster name + description."]
         |
         v
+--------+--------+
|                  |
v                  v
Zugewiesen    Neuer Cluster
(zu Cluster X)  vorgeschlagen
                   |
                   v
           [LLM: "Is this new cluster too similar to any existing?
                  Should they be merged?"]
                   |
            +------+------+
            |             |
            v             v
         Eigenstaendig   Merge-Vorschlag
         (behalten)      → User-Approval
```

### Pattern 3: Goal-Driven Clustering Prompt

```python
GOAL_DRIVEN_CLUSTERING_PROMPT = """
Du analysierst Interview-Feedback fuer folgendes Forschungsziel:
"{research_goal}"

Projekt-Kontext:
{prompt_context}

Bestehende Cluster:
{existing_clusters_with_summaries}

Neue Facts aus Interview #{interview_id}:
{new_facts}

Aufgaben:
1. Ordne jeden Fact dem passendsten bestehenden Cluster zu
2. Wenn ein Fact zu keinem Cluster passt, schlage einen neuen Cluster vor
3. Begruende jede Zuordnung in einem Satz

Antworte als JSON:
{
  "assignments": [
    {"fact_id": "...", "cluster_id": "existing_123", "reasoning": "..."},
    {"fact_id": "...", "cluster_id": "NEW", "new_cluster_name": "...",
     "new_cluster_description": "...", "reasoning": "..."}
  ],
  "merge_suggestions": [
    {"cluster_a": "...", "cluster_b": "...", "reason": "..."}
  ],
  "split_suggestions": [
    {"cluster_id": "...", "reason": "...", "proposed_sub_clusters": ["...", "..."]}
  ]
}
"""
```

### Pattern 4: Self-Correction Validation Prompt

```python
VALIDATION_PROMPT = """
Pruefe die folgende Cluster-Zuordnung auf Qualitaet:

Forschungsziel: "{research_goal}"

Cluster-Uebersicht:
{clusters_with_facts}

Pruefe:
1. KOHAERENZ: Gehoeren alle Facts in einem Cluster thematisch zusammen?
2. BALANCE: Gibt es Cluster die zu gross sind (>15 Facts) und gesplittet
   werden sollten?
3. UEBERLAPPUNG: Gibt es Cluster die zu aehnlich sind und gemergt werden
   sollten?
4. ABDECKUNG: Gibt es unzugeordnete Facts die einem Cluster zugeordnet
   werden koennten?
5. RELEVANZ: Sind die Cluster-Namen praezise und beschreibend?

Antworte als JSON:
{
  "quality_score": 0.0-1.0,
  "issues": [
    {"type": "merge_needed", "cluster_a": "...", "cluster_b": "...",
     "reason": "..."},
    {"type": "split_needed", "cluster_id": "...", "reason": "..."},
    {"type": "reassign", "fact_id": "...", "from_cluster": "...",
     "to_cluster": "...", "reason": "..."},
    {"type": "rename", "cluster_id": "...", "suggested_name": "...",
     "reason": "..."}
  ],
  "overall_assessment": "..."
}
"""
```

---

## 4. Architektur-Empfehlung fuer FeedbackAI

### Gewaehlter Ansatz: TNT-LLM + Clio + GoalEx Hybrid

```
┌──────────────────────────────────────────────────┐
│                 FeedbackAI Clustering             │
├──────────────────────────────────────────────────┤
│                                                  │
│  TNT-LLM Pattern        Clio Pattern             │
│  ┌─────────────┐        ┌───────────────┐        │
│  │ Iterative   │        │ Facet/Fact    │        │
│  │ Taxonomy    │        │ Extraction    │        │
│  │ Generation  │        │ per Interview │        │
│  └──────┬──────┘        └───────┬───────┘        │
│         │                       │                │
│         └──────────┬────────────┘                │
│                    │                             │
│         GoalEx Pattern                           │
│         ┌──────────┴──────────┐                  │
│         │ Goal-Driven         │                  │
│         │ Cluster Assignment  │                  │
│         │ (research_goal)     │                  │
│         └──────────┬──────────┘                  │
│                    │                             │
│         Self-Correction (Few-Shot Pattern)        │
│         ┌──────────┴──────────┐                  │
│         │ LLM validates       │                  │
│         │ + corrects          │                  │
│         │ assignments         │                  │
│         └──────────┬──────────┘                  │
│                    │                             │
│         ┌──────────┴──────────┐                  │
│         │ LangGraph           │                  │
│         │ StateGraph          │                  │
│         │ Orchestration       │                  │
│         └─────────────────────┘                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Warum dieser Ansatz?

| Kriterium | Entscheidung | Begruendung |
|-----------|-------------|-------------|
| Kein HDBSCAN/Embeddings | TNT-LLM + "Clustering as Classification" | Reines Prompt-basiertes Clustering |
| Streaming/Inkrementell | k-LLMmeans Mini-Batch Pattern | Neues Interview → inkrementelle Zuordnung |
| Goal-Driven | GoalEx PAS Pattern | `research_goal` steuert Clustering-Perspektive |
| Self-Correction | Few-Shot Clustering Post-Correction | LangGraph Loop mit max 3 Iterationen |
| Erklaerbarkeit | Clio Facet Pattern | Cluster-Summaries + Reasoning pro Zuordnung |
| Skalierbarkeit | Tiered LLM via OpenRouter | Extraction guenstig, Clustering intelligent |
| Produktions-Beweis | Clio (Millionen Conversations), Anthropic Interviewer | Anthropic nutzt diesen Ansatz selbst |

### OpenRouter Model-Konfiguration

User kann pro Aufgabe den Model-Slug konfigurieren:

| Aufgabe | Empfohlenes Default-Modell | Warum |
|---------|---------------------------|-------|
| Interviewer | `anthropic/claude-sonnet-4` | Empathie, Gespraechsfuehrung |
| Fact Extraction | `anthropic/claude-haiku-4` | Schnell, guenstig, strukturierte Extraktion |
| Clustering / Taxonomy | `anthropic/claude-sonnet-4` | Semantisches Verstaendnis, Goal-Alignment |
| Self-Correction | `anthropic/claude-sonnet-4` | Reasoning, Qualitaetsbewertung |
| Summary Generation | `anthropic/claude-haiku-4` | Zusammenfassung ist einfach |

### Kosten-Schaetzung (100 Interviews, ~500 Facts)

| Schritt | Default Model | Calls | ~Tokens/Call | ~Kosten |
|---------|---------------|-------|-------------|---------|
| Fact Extraction | Haiku | 100 | ~2.000 | ~$0.05 |
| Initial Taxonomy | Sonnet | 1 | ~5.000 | ~$0.08 |
| Fact Assignment | Sonnet | 100 | ~3.000 | ~$4.50 |
| Self-Correction | Sonnet | 3 | ~5.000 | ~$0.23 |
| Summaries | Haiku | ~15 | ~3.000 | ~$0.05 |
| **Total** | | **~219** | | **~$4.91** |

*Preise variieren je nach OpenRouter-Model-Slug. User konfiguriert selbst.*

---

## 5. Inkrementelles Re-Clustering mit Merge/Split-Vorschlaegen

### Entscheidung: Hybrid mit Suggestions

Basierend auf User-Feedback: Inkrementell als Default + LLM-gesteuerte Merge/Split-Vorschlaege + User-Approval + manueller Full-Re-Cluster Button.

### Inkrementeller Flow

```
Neues Interview abgeschlossen
    |
    v
[1] Fact Extraction → Neue Facts
    |
    v
[2] LLM ordnet Facts bestehenden Clustern zu
    ODER schlaegt neue Cluster vor
    |
    v
[3] Wenn neuer Cluster: LLM prueft Aehnlichkeit zu bestehenden
    → Auto-Merge-Vorschlag (User entscheidet)
    |
    v
[4] Wenn Cluster > N Facts: LLM prueft auf Sub-Themen
    → Auto-Split-Vorschlag (User entscheidet)
    |
    v
[5] Vorschlaege als Suggestions im Dashboard
    User bestaetigt oder verwirft
```

### Full Re-Cluster (manueller Trigger)

- Button "Neu berechnen" im Dashboard
- Loescht alle Cluster-Zuordnungen
- Fuehrt komplette TNT-LLM Pipeline neu aus
- Sinnvoll nach vielen manuellen Aenderungen oder bei >50 neuen Interviews

---

## 6. Quellen-Verzeichnis

### Akademische Papers

| Paper | Venue | Jahr | Link |
|-------|-------|------|------|
| TnT-LLM | KDD 2024 | 2024 | [arXiv](https://arxiv.org/abs/2403.12173) |
| Text Clustering as Classification | SIGIR-AP 2025 | 2025 | [arXiv](https://arxiv.org/html/2410.00927v1) |
| GoalEx | EMNLP 2023 | 2023 | [arXiv](https://arxiv.org/abs/2305.13749) |
| k-LLMmeans | arXiv | 2025 | [arXiv](https://arxiv.org/abs/2502.09667) |
| ClusterLLM | EMNLP 2023 | 2023 | [arXiv](https://arxiv.org/abs/2305.14871) |
| Few-Shot Clustering | TACL/MIT Press | 2024 | [MIT Press](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00648/120476) |
| Clio | Anthropic Research | 2024 | [Anthropic](https://www.anthropic.com/research/clio) |

### Code-Repositories

| Repo | Beschreibung | Link |
|------|-------------|------|
| LangGraph TNT-LLM Tutorial | Offizielles LangGraph Notebook | [GitHub](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/tnt-llm/tnt-llm.ipynb) |
| Text-Clustering-via-LLM | ECNU Paper Code | [GitHub](https://github.com/ECNU-Text-Computing/Text-Clustering-via-LLM) |
| GoalEx | Goal-Driven Clustering Code | [GitHub](https://github.com/ZihanWangKi/GoalEx) |
| ClusterLLM | LLM-guided Clustering | [GitHub](https://github.com/zhang-yu-wei/ClusterLLM) |
| OpenClio | Open-Source Clio | [GitHub](https://github.com/Phylliida/OpenClio) |
| Embedding vs Prompting | Side-by-Side Demo | [GitHub](https://github.com/intellectronica/text-clustering-embedding-vs-prompting) |

### Practitioner Resources

| Resource | Link |
|----------|------|
| DataCamp TNT-LLM Tutorial | [DataCamp](https://www.datacamp.com/tutorial/gpt-4o-langgraph-tnt-llm) |
| Chris Ellis: LLM vs Traditional Clustering | [Blog](https://www.chrisellis.dev/articles/comparing-llm-based-vs-traditional-clustering-for-support-conversations) |
| Microsoft ISE: Customer Feedback Insights | [DevBlog](https://devblogs.microsoft.com/ise/insights_generation_from_customer_feedback_using_llms/) |
| Semantic Clustering with LLM Prompts | [Medium](https://medium.com/data-science-collective/tutorial-semantic-clustering-of-user-messages-with-llm-prompts-5308b9b4bc5b) |
| Fenic + LangGraph Agent for Log Clustering | [typedef.ai](https://www.typedef.ai/blog/build-an-llm-agent-for-log-clustering-and-triage) |
| Interview Transcript Analysis (JEDM 2026) | [JEDM](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/1008) |
