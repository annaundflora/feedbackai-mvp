"""Prompt-Templates fuer die Clustering-Pipeline.

Clio-Pattern: Facet Extraction mit GoalEx research_goal-Kontext.
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
