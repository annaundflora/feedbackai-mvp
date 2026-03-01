"""Prompt-Templates fuer die Clustering-Pipeline.

Clio-Pattern: Facet Extraction mit GoalEx research_goal-Kontext.
Erweitert in Slice 3: Clustering-Prompts (TNT-LLM + GoalEx + Clio Hybrid).
"""

FACT_EXTRACTION_PROMPT = """You are a qualitative research analyst. Your task is to extract atomic facts from an interview.

Research Goal: {research_goal}

Interview Text:
{interview_text}

Extract all atomic facts that are relevant to the research goal. Each fact should be:
- A single, self-contained observation or statement
- Directly attributable to this interviewee
- Concrete and specific (not vague)
- Maximum 1000 characters

For each fact, also extract:
- quote: The exact quote from the interview that supports this fact (verbatim, max 500 chars). Use null if transcript quotes are not available.
- confidence: Your confidence that this fact is relevant to the research goal (0.0 to 1.0)

Return ONLY a valid JSON array. No preamble, no explanation.

Format:
[
  {{
    "content": "The user cannot find the settings page after completing onboarding.",
    "quote": "I spent 10 minutes just trying to find where my account settings were.",
    "confidence": 0.95
  }},
  ...
]

If no relevant facts are found, return an empty array: []"""


# --- GENERATE TAXONOMY PROMPT (mode=full, Mini-Batch) ---

GENERATE_TAXONOMY_PROMPT = """You are a qualitative research analyst. Your task is to generate a thematic taxonomy from user interview data.

Research Goal: {research_goal}
{prompt_context_section}

Below are atomic facts extracted from user interviews. Analyze them and propose a set of thematic clusters.

Facts (batch {batch_number} of {total_batches}):
{facts_text}

Already proposed clusters from previous batches:
{existing_taxonomy}

Propose new cluster names that are:
- Directly relevant to the research goal
- Distinct from already proposed clusters (merge with existing if too similar)
- Named with 2-5 words, specific and descriptive
- Not more than 8 clusters total across all batches

Return ONLY a valid JSON array of cluster names. No preamble.

Format: ["Cluster Name 1", "Cluster Name 2", ...]"""


# --- ASSIGN FACTS PROMPT (incremental + full) ---

ASSIGN_FACTS_PROMPT = """You are a qualitative research analyst. Assign each fact to the most appropriate cluster.

Research Goal: {research_goal}
{prompt_context_section}

Available Clusters:
{clusters_text}

Cluster format:
- [id:UUID] ClusterName → existing cluster with a real UUID, use this UUID as cluster_id
- [NEW] ClusterName → proposed cluster without UUID yet, use new_cluster_name with the exact cluster name

Facts to assign:
{facts_text}

Rules:
- For [id:UUID] clusters: set cluster_id to the UUID, set new_cluster_name to null
- For [NEW] clusters: set cluster_id to null, set new_cluster_name to the exact cluster name shown
- If no cluster fits (similarity < 60%): set cluster_id to null, set new_cluster_name to a new name
- NEVER put a cluster name in cluster_id — cluster_id must be a UUID or null

Return ONLY a valid JSON array. No preamble.

Format:
[
  {{"fact_id": "uuid", "cluster_id": "existing-cluster-uuid", "new_cluster_name": null}},
  {{"fact_id": "uuid", "cluster_id": null, "new_cluster_name": "New Cluster Name"}},
  ...
]"""


# --- VALIDATE QUALITY PROMPT ---

VALIDATE_QUALITY_PROMPT = """You are a quality reviewer for qualitative research clustering.

Research Goal: {research_goal}

Current cluster assignments:
{cluster_summary_text}

Evaluate the clustering quality:
1. Are facts within each cluster thematically coherent?
2. Are there obvious duplicates between clusters?
3. Is the cluster size distribution reasonable (no cluster with >60% of all facts)?
4. Are assignments aligned with the research goal?

Return ONLY a valid JSON object. No preamble.

Format:
{{
  "quality_ok": true | false,
  "issues": ["Issue description 1", "Issue description 2"]
}}

If quality_ok is true, issues should be an empty list."""


# --- REFINE CLUSTERS PROMPT ---

REFINE_CLUSTERS_PROMPT = """You are a qualitative research analyst. Refine the cluster assignments based on quality issues.

Research Goal: {research_goal}

Quality Issues identified:
{issues_text}

Current assignments (to refine):
{cluster_summary_text}

Provide corrected assignments for facts that need to be moved. Only include facts that need to change.

Return ONLY a valid JSON array of corrections. No preamble.

Format:
[
  {{"fact_id": "uuid", "cluster_id": "target-cluster-uuid", "new_cluster_name": null}},
  ...
]"""


# --- GENERATE SUMMARIES PROMPT ---

GENERATE_SUMMARIES_PROMPT = """You are a qualitative research analyst. Write a concise summary for a thematic cluster.

Research Goal: {research_goal}

Cluster Name: {cluster_name}

Facts in this cluster:
{facts_text}

Write a 2-4 sentence summary that:
- Captures the main theme across all facts
- Is written from the user's perspective
- Highlights the most significant pattern
- Is relevant to the research goal

Return ONLY the summary text. No preamble, no quotes."""


# --- CHECK SUGGESTIONS PROMPT ---

CHECK_SUGGESTIONS_PROMPT = """You are a qualitative research analyst. Check if any clusters should be merged or split.

Research Goal: {research_goal}

Current clusters with fact counts and summaries:
{clusters_text}

Check for:
1. MERGE opportunities: Clusters that are semantically very similar (>80% overlap in themes)
2. SPLIT opportunities: Clusters with many facts (>{split_threshold}) that contain distinct sub-themes

Return ONLY a valid JSON array. Return empty array [] if no suggestions. No preamble.

Format:
[
  {{
    "type": "merge",
    "source_cluster_id": "uuid",
    "target_cluster_id": "uuid",
    "similarity_score": 0.85,
    "reason": "Brief explanation"
  }},
  {{
    "type": "split",
    "source_cluster_id": "uuid",
    "proposed_subclusters": ["Subcluster Name 1", "Subcluster Name 2"],
    "reason": "Brief explanation"
  }}
]"""
