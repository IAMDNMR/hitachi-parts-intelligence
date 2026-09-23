"""
backend/app/api/v1/part_enrichment.py

Migrated from frontend/api/part-enrichment.js + frontend/api/_lib/enrichment.js
(the Node/Vercel-style layer, now retired). Same query, same response shape,
now served over the single FastAPI backend using the shared Neo4j driver
(app.db.neo4j.connection) instead of a second, separate JS driver.

Verified Neo4j information for the EXISTING Parts Store catalogue, keyed by
Part Number for an exact (never fuzzy) match on the frontend. This does not
replace, list, or count parts — the static catalogue remains the sole source
of which products exist, their images, and their identity. If this endpoint
is unreachable, the Parts Store must keep working exactly as it does today;
nothing here is load-bearing for the catalogue itself.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.db.neo4j.connection import get_neo4j_session

router = APIRouter(tags=["Part Enrichment"])

# Same vocabulary translation as the retired Node route: Aura's
# HAS_PART_FITMENT.evidence values versus the level strings the frontend's
# compatibility helpers already understand.
EVIDENCE_TO_LEVEL = {
    "EXACT_MODEL": "EXACT MODEL",
    "MODEL_RANGE": "MODEL/RANGE",
    "CATEGORY": "CATEGORY",
}


def get_enrichment_by_part_number(session) -> Dict[str, Any]:
    result = session.run(
        """
        MATCH (p:Part)
        WHERE p.part_number IS NOT NULL
        OPTIONAL MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p)
        WITH p, collect(
            CASE WHEN m IS NULL THEN NULL ELSE { machineId: m.machine_id, model: m.model, evidence: r.evidence } END
        ) AS rawFitment
        WITH p, [x IN rawFitment WHERE x IS NOT NULL] AS fitment
        WHERE size(fitment) > 0
        RETURN p.part_number AS partNumber, p.part_id AS partId, fitment
        """
    )

    by_part_number: Dict[str, Any] = {}
    for record in result:
        part_number = record["partNumber"]
        fitment = record["fitment"]
        by_part_number[part_number] = {
            "partId": record["partId"],
            "compatibleMachines": [
                {
                    "machineId": f["machineId"],
                    "model": f["model"],
                    "level": EVIDENCE_TO_LEVEL.get(f["evidence"], "CATEGORY"),
                }
                for f in fitment
            ],
        }
    return by_part_number


@router.get("/part-enrichment")
def part_enrichment(session=Depends(get_neo4j_session)):
    enrichment = get_enrichment_by_part_number(session)
    return {"enrichment": enrichment}
