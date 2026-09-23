"""
backend/app/api/v1/quote_request.py

Migrated from frontend/api/quote-request.js + frontend/api/_lib/quoteRequest.js
(the Node/Vercel-style layer, now retired). The graph write shape is
preserved EXACTLY as the Node version wrote it — this is the shape that was
actually in production use — using the shared Neo4j driver
(app.db.neo4j.connection) instead of a second, separate JS driver:

    (:Customer)-[:SUBMITTED]->(:PartsInquiry)-[:REQUESTS]->(:RequestedPart)-[:FOR_PART]->(:Part)

Name, email and phone are required (note is not) — the same rule the
PartsStore form itself enforces, checked again here since a request can
reach this endpoint without going through that form. Beyond "present and
email-shaped", nothing about a customer detail is verified, invented, or
backfilled — whatever the visitor typed is what gets stored.
"""

import json
import re
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.neo4j.connection import get_neo4j_session
from app.logging_config.logger import logger

router = APIRouter(tags=["Quote Request"])

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class QuoteRequestItem(BaseModel):
    id: Optional[str] = None
    name: str
    qty: int
    machine: Optional[str] = None
    partNumber: Optional[str] = None


class QuoteRequestPayload(BaseModel):
    name: str
    email: str
    phone: str
    note: Optional[str] = None
    items: List[QuoteRequestItem]


def _bad_request(message: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=400, detail=message)


@router.post("/quote-request")
def submit_quote_request(
    payload: QuoteRequestPayload,
    session=Depends(get_neo4j_session),
):
    if not payload.name.strip() or not payload.email.strip() or not payload.phone.strip():
        _bad_request("Name, email and phone are required.")
    if not EMAIL_PATTERN.match(payload.email.strip()):
        _bad_request("Enter a valid email address.")
    if len(payload.items) == 0:
        _bad_request("At least one part is required.")

    name = payload.name.strip()
    email = payload.email.strip()
    phone = payload.phone.strip()
    note = payload.note.strip() if payload.note and payload.note.strip() else None

    inquiry_id = f"inq-{uuid.uuid4()}"
    items = [item.model_dump() for item in payload.items]
    requested_part_count = len(items)
    neo4j_status = "FAILED"

    try:
        result = session.execute_write(
            lambda tx: tx.run(
                """
                MERGE (c:Customer {email: $email})
                ON CREATE SET c.name = $name, c.phone = $phone, c.createdAt = datetime()
                ON MATCH SET c.name = $name, c.phone = $phone, c.updatedAt = datetime()
                CREATE (i:PartsInquiry {
                    id: $inquiryId,
                    name: $name,
                    email: $email,
                    phone: $phone,
                    note: $note,
                    itemsJson: $itemsJson,
                    createdAt: datetime()
                })
                CREATE (c)-[:SUBMITTED]->(i)
                WITH i
                UNWIND $items AS item
                CREATE (rp:RequestedPart {
                    requested_part_id: item.requestedPartId,
                    part_id: item.id,
                    part_name: item.name,
                    quantity: item.qty,
                    machine: item.machine
                })
                CREATE (i)-[:REQUESTS]->(rp)
                WITH i, rp, item
                OPTIONAL MATCH (p:Part {part_number: item.partNumber})
                FOREACH (_ IN CASE WHEN item.partNumber IS NOT NULL AND p IS NOT NULL THEN [1] ELSE [] END |
                    CREATE (rp)-[:FOR_PART]->(p)
                )
                RETURN i.id AS inquiryId, count(rp) AS requestedPartCount
                """,
                {
                    "inquiryId": inquiry_id,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "note": note,
                    "itemsJson": json.dumps(items),
                    "items": [
                        {
                            "requestedPartId": f"{inquiry_id}-{index}",
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "qty": item.get("qty"),
                            "machine": item.get("machine"),
                            "partNumber": item.get("partNumber"),
                        }
                        for index, item in enumerate(items)
                    ],
                },
            ).data()
        )
        if result:
            requested_part_count = result[0]["requestedPartCount"]
            neo4j_status = "SUCCESS"
    except Exception as err:  # noqa: BLE001 - mirrors the Node version's catch-all degrade
        logger.warning(f"[Quote Reconciliation] Neo4j write failed: {err}")
        neo4j_status = "DEGRADED"

    return {
        "ok": True,
        "inquiryId": inquiry_id,
        "requestedPartCount": requested_part_count,
        "projectionStatus": neo4j_status,
    }
