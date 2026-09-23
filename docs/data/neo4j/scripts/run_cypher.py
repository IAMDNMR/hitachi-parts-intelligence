"""
docs/data/neo4j/scripts/run_cypher.py

Ad-hoc Cypher runner against the project's real Neo4j AuraDB instance,
using the same driver/config as the FastAPI backend
(backend/app/db/neo4j/connection.py -> backend/app/config.py).

Usage:
    python docs/data/neo4j/scripts/run_cypher.py "MATCH (n) RETURN count(n) AS c"

Prints each result record as a dict, one per line.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend"))

from app.db.neo4j.connection import get_neo4j_driver
from app.config import settings


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python run_cypher.py \"<cypher query>\"", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    driver = get_neo4j_driver()
    db = getattr(settings, "NEO4J_DATABASE", None) or None
    session_kwargs = {"database": db} if db else {}

    with driver.session(**session_kwargs) as session:
        result = session.run(query)
        records = [dict(r) for r in result]
        summary = result.consume()

    for r in records:
        print(r)
    print(
        f"--- counters: nodes_created={summary.counters.nodes_created} "
        f"nodes_deleted={summary.counters.nodes_deleted} "
        f"relationships_deleted={summary.counters.relationships_deleted} "
        f"properties_set={summary.counters.properties_set} ---"
    )


if __name__ == "__main__":
    main()
