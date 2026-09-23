"""
backend/app/audit/service.py

Append-only audit log using Neo4j AuditRecord nodes.
"""
import json
import uuid
from typing import Any, Dict, Optional

from app.logging_config.logger import logger


def record_audit_event(
    session,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
    source: str = "SYSTEM",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    test_run_id: Optional[str] = None,
) -> str:
    audit_id = f"aud-{uuid.uuid4()}"
    details_json = json.dumps(details) if details else None

    cypher = """
        CREATE (a:AuditRecord {
            id:            $id,
            actorId:       $actor_id,
            actorRole:     $actor_role,
            action:        $action,
            entityType:    $entity_type,
            entityId:      $entity_id,
            previousState: $previous_state,
            newState:      $new_state,
            source:        $source,
            requestId:     $request_id,
            correlationId: $correlation_id,
            detailsJson:   $details_json,
            createdAt:     datetime()
        })
    """
    params = {
        "id": audit_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "source": source,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "details_json": details_json,
    }

    if test_run_id:
        cypher = cypher.rstrip() + "\nSET a.testRunId = $test_run_id"
        params["test_run_id"] = test_run_id

    try:
        session.run(cypher, params).consume()
        logger.info(f"Audit record created: {action} on {entity_type}:{entity_id}")
    except Exception as e:
        logger.error(f"Failed to insert audit record: {e}")
        raise

    return audit_id
