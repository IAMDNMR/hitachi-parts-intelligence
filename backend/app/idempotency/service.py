"""
backend/app/idempotency/service.py

Idempotency cache using Neo4j IdempotencyRecord nodes.
"""
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

from app.errors.exceptions import ConflictError


def calculate_request_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_idempotency(
    session,
    endpoint: str,
    idempotency_key: str,
    request_payload: Any,
) -> Tuple[bool, Optional[int], Optional[Dict[str, Any]]]:
    request_hash = calculate_request_hash(request_payload)

    cypher = """
        MATCH (i:IdempotencyRecord {idempotencyKey: $key, endpoint: $endpoint})
        RETURN i.requestHash AS requestHash,
               i.responseStatus AS responseStatus,
               i.responseBodyJson AS responseBodyJson,
               i.expiresAt AS expiresAt
    """
    result = session.run(cypher, {"key": idempotency_key, "endpoint": endpoint}).single()

    if result:
        db_hash = result["requestHash"]
        if db_hash != request_hash:
            raise ConflictError("Idempotency key reused with different request payload")
        return True, result["responseStatus"], json.loads(result["responseBodyJson"])

    return False, None, None


def save_idempotency_record(
    session,
    endpoint: str,
    idempotency_key: str,
    request_payload: Any,
    response_status: int,
    response_body: Dict[str, Any],
    ttl_hours: int = 24,
    test_run_id: Optional[str] = None,
) -> None:
    request_hash = calculate_request_hash(request_payload)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()

    cypher = """
        MERGE (i:IdempotencyRecord {idempotencyKey: $key, endpoint: $endpoint})
        ON CREATE SET
            i.requestHash      = $hash,
            i.responseStatus   = $status,
            i.responseBodyJson = $body,
            i.createdAt        = datetime(),
            i.expiresAt        = $expires_at
    """
    params = {
        "key": idempotency_key,
        "endpoint": endpoint,
        "hash": request_hash,
        "status": response_status,
        "body": json.dumps(response_body),
        "expires_at": expires_at,
    }

    if test_run_id:
        cypher += "\nON MATCH SET i.testRunId = $test_run_id\nSET i.testRunId = $test_run_id"
        params["test_run_id"] = test_run_id

    session.run(cypher, params).consume()
