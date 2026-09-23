"""
backend/app/modules/intelligence/ranking.py

Scoring formula for candidate Parts. Documented explicitly per spec
requirement 11 ("no fabricated percentages").

match_score is a weighted combination of which retrieval stage(s) found the
part, in [0, 1]:

  EXACT_PART_NUMBER match          -> 1.0 (always ranked first)
  LEXICAL match on part_name       -> 0.7
  LEXICAL match on description     -> 0.5
  LEXICAL match on category        -> 0.4
  SEMANTIC (vector) match          -> 0.6  (only used when embeddings are
                                             available; see providers.py —
                                             currently never available in
                                             this environment)
  machine_model filter matched via graph fitment -> +0.2 bonus (capped at 1.0)

When a part is found by multiple stages, its score is the MAX of the
individual stage scores, plus the fitment bonus. This is a simple,
inspectable heuristic — not a trained model — and is documented here so the
UI never displays an unexplained percentage.
"""

from typing import Dict, List

STAGE_SCORES: Dict[str, float] = {
    "EXACT_PART_NUMBER": 1.0,
    "LEXICAL_NAME": 0.7,
    "LEXICAL_DESCRIPTION": 0.5,
    "LEXICAL_CATEGORY": 0.4,
    "SEMANTIC": 0.6,
}

FITMENT_BONUS = 0.2


def score_candidate(match_methods: List[str], fitment_matched: bool) -> float:
    if not match_methods:
        base = 0.0
    else:
        base = max(STAGE_SCORES.get(m, 0.3) for m in match_methods)
    if fitment_matched:
        base = min(1.0, base + FITMENT_BONUS)
    return round(base, 2)
