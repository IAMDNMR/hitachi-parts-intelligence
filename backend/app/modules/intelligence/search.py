"""
backend/app/modules/intelligence/search.py

Candidate Part retrieval: exact / lexical / semantic. Neo4j-only — no
second search database.

- Exact: direct match on Part.part_id or Part.part_number.
- Lexical: Neo4j full-text index over part_name/description/part_category/
  part_subcategory (created idempotently in app.db.neo4j.schema).
- Semantic: Neo4j vector index, used only if an EmbeddingProvider is
  actually available (see providers.py). In this environment no embedding
  provider is configured, so semantic search is skipped and this is
  reported back to the caller as a degraded/unavailable search mode rather
  than silently pretending to run it.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.modules.intelligence.providers import get_embedding_provider
from app.modules.intelligence.ranking import score_candidate

PART_FULLTEXT_INDEX = "part_fulltext_search"


def exact_search(session, term: str) -> List[Dict[str, Any]]:
    result = session.run(
        """
        MATCH (p:Part)
        WHERE p.part_id = $term OR p.part_number = $term
        RETURN p
        """,
        {"term": term},
    ).data()
    return [r["p"] for r in result]


def lexical_search(session, term: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Full-text search via the native Neo4j index. Falls back to a plain
    CONTAINS scan if the index does not exist yet (e.g. schema not applied)."""
    try:
        result = session.run(
            """
            CALL db.index.fulltext.queryNodes($index, $term) YIELD node, score
            RETURN node AS p, score
            LIMIT $limit
            """,
            {"index": PART_FULLTEXT_INDEX, "term": term, "limit": limit},
        ).data()
        return [r["p"] for r in result]
    except Exception:
        result = session.run(
            """
            MATCH (p:Part)
            WHERE toLower(p.part_name) CONTAINS toLower($term)
               OR toLower(coalesce(p.description, '')) CONTAINS toLower($term)
               OR toLower(coalesce(p.part_category, '')) CONTAINS toLower($term)
               OR toLower(coalesce(p.part_subcategory, '')) CONTAINS toLower($term)
            RETURN p
            LIMIT $limit
            """,
            {"term": term, "limit": limit},
        ).data()
        return [r["p"] for r in result]


def semantic_search(session, term: str, limit: int = 15) -> Tuple[List[Dict[str, Any]], bool]:
    """Returns (candidates, was_used). was_used=False whenever no embedding
    provider is configured — callers must report this honestly rather than
    claiming semantic search ran."""
    provider = get_embedding_provider()
    if not provider.is_available():
        return [], False
    vector = provider.embed(term)
    if vector is None:
        return [], False
    try:
        result = session.run(
            """
            CALL db.index.vector.queryNodes('part_embedding_index', $limit, $vector)
            YIELD node, score
            RETURN node AS p, score
            """,
            {"limit": limit, "vector": vector},
        ).data()
        return [r["p"] for r in result], True
    except Exception:
        return [], False


def machine_fitted_part_ids(session, machine_model: str) -> List[str]:
    """Part IDs with graph-confirmed fitment to a machine model (exact or
    fuzzy model match on Machine.model)."""
    result = session.run(
        """
        MATCH (m:Machine)-[:HAS_PART_FITMENT]->(p:Part)
        WHERE toUpper(m.model) = toUpper($model) OR toUpper(m.model) CONTAINS toUpper($model)
        RETURN DISTINCT p.part_id AS part_id
        """,
        {"model": machine_model},
    ).data()
    return [r["part_id"] for r in result]
