"""
backend/app/modules/service/service.py

Phase 8 Dealer & Service domain service.
Implements the documented HCME service lifecycle:
    OPEN → PART_RECEIVED → IN_PROGRESS → PART_INSTALLED → COMPLETED (or CANCELLED)
And closes the end-to-end fulfilment journey in Neo4j AuraDB.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.audit.service import record_audit_event
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.integrations.contracts.service import ServiceScheduleRequest
from app.integrations.factory import get_service_provider
from app.logging_config.logger import logger


def _get_raw_service_job(session, service_job_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        RETURN sj
        """,
        {"id": service_job_id},
    ).single()
    if not row:
        raise NotFoundError(f"ServiceJob '{service_job_id}' not found")
    return dict(row["sj"])


def create_service_job(
    session,
    order_id: str,
    service_type: str = "PARTS_INSTALLATION",
    technician_role: Optional[str] = "CERTIFIED_SERVICE_TECHNICIAN",
    notes: Optional[str] = None,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new ServiceJob linked to an existing Order, Shipment, DealerBranch, Part, and Machine.
    Initial state is 'OPEN'.
    """
    # 1. Retrieve Order
    order_row = session.run(
        """
        MATCH (o:Order {id: $order_id})
        OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
        OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        RETURN o, sh, fr
        """,
        {"order_id": order_id},
    ).single()

    if not order_row or not order_row["o"]:
        raise NotFoundError(f"Order '{order_id}' not found")

    order = dict(order_row["o"])
    shipment = dict(order_row["sh"]) if order_row["sh"] else None
    fulfilment_req = dict(order_row["fr"]) if order_row["fr"] else None

    # Order must be in a valid progressive state
    valid_order_states = {"ACCEPTED", "ALLOCATED", "SHIPPED", "DELIVERED", "FULFILLED", "COMPLETED"}
    if order.get("status") not in valid_order_states:
        raise ConflictError(
            f"Cannot create ServiceJob for Order '{order_id}' in status '{order.get('status')}'. "
            f"Order must be in one of {valid_order_states}."
        )

    # Check if a ServiceJob already exists for this order
    existing_sj = session.run(
        "MATCH (o:Order {id: $order_id})-[:HAS_SERVICE_JOB]->(sj:ServiceJob) RETURN sj.service_job_id AS id",
        {"order_id": order_id},
    ).single()
    if existing_sj:
        return get_service_job(session, existing_sj["id"])

    # 2. Determine DealerBranch, Part, Machine
    dealer_id = order.get("destinationBranchId") or "DLR-001"
    part_number = order.get("partNumber")
    shipment_id = shipment.get("shipment_id") if shipment else None

    machine_context = (fulfilment_req.get("machineContext") if fulfilment_req else None) or order.get("machineContext")

    service_job_id = f"SJ-{uuid.uuid4().hex[:8].upper()}"
    work_order_num = f"WO-EU-{uuid.uuid4().hex[:6].upper()}"
    event_id = f"sevt-{uuid.uuid4()}"

    # Schedule via ServiceProvider
    service_prov = get_service_provider()
    sched_result = service_prov.schedule_service(
        ServiceScheduleRequest(
            order_id=order_id,
            dealer_id=dealer_id,
            part_number=part_number or "",
            machine_context=machine_context,
            service_type=service_type,
            notes=notes,
        )
    )
    ext_job_id = sched_result.external_job_id if sched_result else None
    synced_at_str = datetime.now(timezone.utc).isoformat()
    data_source_str = sched_result.data_source if (sched_result and sched_result.data_source) else "SYNTHETIC_DEMO"

    # 3. Create ServiceJob node and attach relationships
    session.run(
        """
        CREATE (sj:ServiceJob {
            service_job_id:    $service_job_id,
            order_id:          $order_id,
            shipment_id:       $shipment_id,
            dealer_id:         $dealer_id,
            status:            'OPEN',
            service_type:      $service_type,
            work_order_number: $work_order_num,
            notes:             $notes,
            synthetic:         true,
            data_source:       $data_source,
            external_job_id:   $external_job_id,
            synced_at:         $synced_at,
            provenance:        'INTERNAL_SERVICE_WORKFLOW',
            createdAt:         datetime(),
            updatedAt:         datetime(),
            testRunId:         $test_run_id
        })
        """,
        {
            "service_job_id": service_job_id,
            "order_id": order_id,
            "shipment_id": shipment_id,
            "dealer_id": dealer_id,
            "service_type": service_type,
            "work_order_num": work_order_num,
            "notes": notes,
            "data_source": data_source_str,
            "external_job_id": ext_job_id,
            "synced_at": synced_at_str,
            "test_run_id": test_run_id,
        },
    ).consume()

    # Link Order, Shipment, DealerBranch, Part, Machine, FulfilmentRequest
    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $service_job_id})
        MATCH (o:Order {id: $order_id})
        MERGE (o)-[:HAS_SERVICE_JOB]->(sj)
        WITH sj, o
        OPTIONAL MATCH (sh:Shipment {shipment_id: $shipment_id})
        FOREACH (s IN CASE WHEN sh IS NOT NULL THEN [sh] ELSE [] END |
            MERGE (s)-[:HAS_SERVICE_JOB]->(sj)
        )
        WITH sj, o
        OPTIONAL MATCH (d:DealerBranch {dealer_id: $dealer_id})
        FOREACH (dlr IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END |
            MERGE (dlr)-[:PERFORMS_SERVICE]->(sj)
        )
        WITH sj, o
        OPTIONAL MATCH (p:Part) WHERE p.part_number = $part_number OR p.part_id = $part_number
        FOREACH (pt IN CASE WHEN p IS NOT NULL THEN [p] ELSE [] END |
            MERGE (sj)-[:FOR_PART]->(pt)
        )
        WITH sj, o
        OPTIONAL MATCH (m:Machine) WHERE m.machine_id = $machine_context OR m.model = $machine_context
        FOREACH (mc IN CASE WHEN m IS NOT NULL THEN [m] ELSE [] END |
            MERGE (sj)-[:FOR_MACHINE]->(mc)
        )
        WITH sj, o
        OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        FOREACH (f IN CASE WHEN fr IS NOT NULL THEN [fr] ELSE [] END |
            MERGE (f)-[:HAS_SERVICE_JOB]->(sj)
        )
        """,
        {
            "service_job_id": service_job_id,
            "order_id": order_id,
            "shipment_id": shipment_id,
            "dealer_id": dealer_id,
            "part_number": part_number,
            "machine_context": machine_context,
        },
    ).consume()

    # 4. Create initial ServiceEvent
    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $service_job_id})
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'CREATED',
            description:     'Service Job registered and awaiting shipment delivery at dealer branch.',
            technician_role: $technician_role,
            notes:           $notes,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "service_job_id": service_job_id,
            "event_id": event_id,
            "technician_role": technician_role or "CERTIFIED_SERVICE_TECHNICIAN",
            "notes": notes or "Awaiting delivery",
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SERVICE_JOB_CREATED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=None,
        new_state="OPEN",
        details={
            "order_id": order_id,
            "dealer_id": dealer_id,
            "service_type": service_type,
            "work_order_number": work_order_num,
        },
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def receive_part(
    session,
    service_job_id: str,
    condition_notes: Optional[str] = None,
    technician_role: Optional[str] = "DEALER_PARTS_INSPECTOR",
    actor_id: str = "SYSTEM",
    actor_role: str = "DEALER",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 8: Dealer confirms physical receipt of part.
    Enforces that the linked shipment has reached 'DELIVERED'.
    Transitions OPEN → PART_RECEIVED.
    """
    sj = _get_raw_service_job(session, service_job_id)
    if sj["status"] != "OPEN":
        raise ConflictError(
            f"Cannot receive part for ServiceJob '{service_job_id}' in status '{sj['status']}'. "
            f"Requires status 'OPEN'."
        )

    # Verify linked shipment delivery status per DEALER_SERVICE_PROCESS.md
    shipment_res = session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        OPTIONAL MATCH (sj)<-[:HAS_SERVICE_JOB]-(sh:Shipment)
        OPTIONAL MATCH (sj)<-[:HAS_SERVICE_JOB]-(o:Order)-[:HAS_SHIPMENT]->(sh2:Shipment)
        RETURN coalesce(sh, sh2) AS shipment
        """,
        {"id": service_job_id},
    ).single()

    linked_shipment = dict(shipment_res["shipment"]) if shipment_res and shipment_res["shipment"] else None

    if linked_shipment and linked_shipment.get("status") != "DELIVERED":
        raise ConflictError(
            f"Cannot receive part for ServiceJob '{service_job_id}'. "
            f"Linked shipment '{linked_shipment.get('shipment_id')}' is currently '{linked_shipment.get('status')}'. "
            f"Shipment must be DELIVERED before dealer receipt can be confirmed."
        )

    event_id = f"sevt-{uuid.uuid4()}"
    desc = "Part physically received, verified against order specification, and staged for workshop."
    if condition_notes:
        desc += f" Condition notes: {condition_notes}"

    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        SET sj.status = 'PART_RECEIVED',
            sj.received_at = datetime(),
            sj.updatedAt = datetime()
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'PART_RECEIVED',
            description:     $desc,
            technician_role: $technician_role,
            notes:           $notes,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "id": service_job_id,
            "event_id": event_id,
            "desc": desc,
            "technician_role": technician_role or "DEALER_PARTS_INSPECTOR",
            "notes": condition_notes,
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SERVICE_PART_RECEIVED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="OPEN",
        new_state="PART_RECEIVED",
        details={"condition_notes": condition_notes},
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def start_service(
    session,
    service_job_id: str,
    technician_role: Optional[str] = "CERTIFIED_SERVICE_TECHNICIAN",
    notes: Optional[str] = None,
    actor_id: str = "SYSTEM",
    actor_role: str = "TECHNICIAN",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 9: Technician begins installation / maintenance work.
    Transitions PART_RECEIVED → IN_PROGRESS.
    """
    sj = _get_raw_service_job(session, service_job_id)
    if sj["status"] != "PART_RECEIVED":
        raise ConflictError(
            f"Cannot start service for ServiceJob '{service_job_id}' in status '{sj['status']}'. "
            f"Requires status 'PART_RECEIVED'."
        )

    event_id = f"sevt-{uuid.uuid4()}"
    desc = "Technician initiated service work order and machine preparation."
    if notes:
        desc += f" Notes: {notes}"

    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        SET sj.status = 'IN_PROGRESS',
            sj.started_at = datetime(),
            sj.updatedAt = datetime()
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'IN_PROGRESS',
            description:     $desc,
            technician_role: $technician_role,
            notes:           $notes,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "id": service_job_id,
            "event_id": event_id,
            "desc": desc,
            "technician_role": technician_role or "CERTIFIED_SERVICE_TECHNICIAN",
            "notes": notes,
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SERVICE_STARTED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="PART_RECEIVED",
        new_state="IN_PROGRESS",
        details={"notes": notes},
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def install_part(
    session,
    service_job_id: str,
    installation_notes: Optional[str] = None,
    technician_role: Optional[str] = "CERTIFIED_SERVICE_TECHNICIAN",
    actor_id: str = "SYSTEM",
    actor_role: str = "TECHNICIAN",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 9: Part physically installed on machine.
    Transitions IN_PROGRESS → PART_INSTALLED.
    """
    sj = _get_raw_service_job(session, service_job_id)
    if sj["status"] != "IN_PROGRESS":
        raise ConflictError(
            f"Cannot mark part installed for ServiceJob '{service_job_id}' in status '{sj['status']}'. "
            f"Requires status 'IN_PROGRESS'."
        )

    event_id = f"sevt-{uuid.uuid4()}"
    desc = "OEM replacement component physically installed, fitted, and torqued to factory specifications."
    if installation_notes:
        desc += f" Details: {installation_notes}"

    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        SET sj.status = 'PART_INSTALLED',
            sj.installed_at = datetime(),
            sj.updatedAt = datetime()
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'PART_INSTALLED',
            description:     $desc,
            technician_role: $technician_role,
            notes:           $notes,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "id": service_job_id,
            "event_id": event_id,
            "desc": desc,
            "technician_role": technician_role or "CERTIFIED_SERVICE_TECHNICIAN",
            "notes": installation_notes,
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SERVICE_PART_INSTALLED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="IN_PROGRESS",
        new_state="PART_INSTALLED",
        details={"installation_notes": installation_notes},
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def complete_service(
    session,
    service_job_id: str,
    signoff_notes: Optional[str] = None,
    technician_role: Optional[str] = "WORKSHOP_MANAGER",
    actor_id: str = "SYSTEM",
    actor_role: str = "WORKSHOP_MANAGER",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 10: Service completed and closed.
    Transitions PART_INSTALLED → COMPLETED.
    Per DEALER_SERVICE_PROCESS.md §3: If linked Shipment is DELIVERED and Service is COMPLETED,
    the linked FulfilmentRequest transitions to COMPLETED, closing the end-to-end journey.
    """
    sj = _get_raw_service_job(session, service_job_id)
    if sj["status"] != "PART_INSTALLED":
        raise ConflictError(
            f"Cannot complete ServiceJob '{service_job_id}' in status '{sj['status']}'. "
            f"Requires status 'PART_INSTALLED'."
        )

    event_id = f"sevt-{uuid.uuid4()}"
    desc = "Quality inspection passed, functional testing verified, and service work order signed off."
    if signoff_notes:
        desc += f" Signoff notes: {signoff_notes}"

    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        SET sj.status = 'COMPLETED',
            sj.completed_at = datetime(),
            sj.updatedAt = datetime()
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'COMPLETED',
            description:     $desc,
            technician_role: $technician_role,
            notes:           $notes,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "id": service_job_id,
            "event_id": event_id,
            "desc": desc,
            "technician_role": technician_role or "WORKSHOP_MANAGER",
            "notes": signoff_notes,
            "test_run_id": test_run_id,
        },
    ).consume()

    # Close FulfilmentRequest if linked.
    # Bug fix (Phase 10B): the actual graph shape is
    #   FulfilmentRequest -[:HAS_ORDER]-> Order -[:HAS_SHIPMENT]-> Shipment -[:HAS_SERVICE_JOB]-> ServiceJob
    # (see docs/business-process/PROCESS_STATES.md — the Fulfilment Request
    # only reaches COMPLETED when its Shipment is DELIVERED and its Service
    # Job is COMPLETED). The previous query looked for a direct
    # FulfilmentRequest-[:HAS_SERVICE_JOB]->ServiceJob or
    # Order-[:HAS_SERVICE_JOB]->ServiceJob edge, neither of which exists in
    # this graph, so fReq.status never advanced past 'ORDERED' even after a
    # real shipment delivered and its service job completed.
    # receive_part() already refuses PART_RECEIVED unless the linked
    # Shipment is DELIVERED, so by the time we reach here that is guaranteed;
    # the explicit sh.status check below is defense in depth, matching the
    # documented cross-state-machine rule.
    closed = session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        OPTIONAL MATCH (sh:Shipment)-[:HAS_SERVICE_JOB]->(sj)
        OPTIONAL MATCH (o1:Order)-[:HAS_SHIPMENT]->(sh)
        OPTIONAL MATCH (fr1:FulfilmentRequest)-[:HAS_ORDER]->(o1)
        WITH sj, sh, coalesce(fr1, null) AS fReq
        WHERE fReq IS NOT NULL AND (sh IS NULL OR sh.status = 'DELIVERED')
        SET fReq.status = 'COMPLETED',
            fReq.completed_at = datetime(),
            fReq.updatedAt = datetime()
        RETURN fReq.id AS id
        """,
        {"id": service_job_id},
    ).single()
    closed_fulfilment_request_id = closed["id"] if closed else None

    record_audit_event(
        session=session,
        action="SERVICE_COMPLETED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="PART_INSTALLED",
        new_state="COMPLETED",
        details={"signoff_notes": signoff_notes},
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def cancel_service_job(
    session,
    service_job_id: str,
    reason: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cancel an active service job (OPEN, PART_RECEIVED, or IN_PROGRESS).
    Cannot cancel COMPLETED service jobs.
    """
    sj = _get_raw_service_job(session, service_job_id)
    if sj["status"] in ("COMPLETED", "CANCELLED"):
        raise ConflictError(
            f"Cannot cancel ServiceJob '{service_job_id}' in terminal status '{sj['status']}'."
        )

    event_id = f"sevt-{uuid.uuid4()}"
    desc = f"Service job cancelled: {reason}"

    session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        SET sj.status = 'CANCELLED',
            sj.cancelled_at = datetime(),
            sj.cancel_reason = $reason,
            sj.updatedAt = datetime()
        CREATE (e:ServiceEvent {
            id:              $event_id,
            event_type:      'CANCELLED',
            description:     $desc,
            technician_role: 'SYSTEM',
            notes:           $reason,
            timestamp:       datetime(),
            synthetic:       true,
            data_source:     'SYNTHETIC_DEMO',
            testRunId:       $test_run_id
        })
        MERGE (sj)-[:HAS_EVENT]->(e)
        """,
        {
            "id": service_job_id,
            "event_id": event_id,
            "desc": desc,
            "reason": reason,
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SERVICE_CANCELLED",
        entity_type="SERVICE_JOB",
        entity_id=service_job_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=sj["status"],
        new_state="CANCELLED",
        details={"reason": reason},
        test_run_id=test_run_id,
    )

    return get_service_job(session, service_job_id)


def get_service_job(session, service_job_id: str) -> Dict[str, Any]:
    """
    Retrieve ServiceJob details and its chronological event timeline from Neo4j AuraDB.
    """
    row = session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        OPTIONAL MATCH (d:DealerBranch {dealer_id: sj.dealer_id})
        OPTIONAL MATCH (sj)-[:FOR_PART]->(p:Part)
        OPTIONAL MATCH (sj)-[:FOR_MACHINE]->(m:Machine)
        OPTIONAL MATCH (sj)-[:HAS_EVENT]->(e:ServiceEvent)
        WITH sj, d, p, m, e
        ORDER BY e.timestamp ASC
        WITH sj, d, p, m, collect(e) AS raw_events
        RETURN sj, d, p, m, raw_events
        """,
        {"id": service_job_id},
    ).single()

    if not row or not row["sj"]:
        raise NotFoundError(f"ServiceJob '{service_job_id}' not found")

    sj = dict(row["sj"])
    d = dict(row["d"]) if row["d"] else {}
    p = dict(row["p"]) if row["p"] else {}
    m = dict(row["m"]) if row["m"] else {}

    events = []
    for ev in row["raw_events"]:
        if ev:
            ed = dict(ev)
            ts = ed.get("timestamp")
            if hasattr(ts, "isoformat"):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            events.append({
                "id": ed.get("id"),
                "event_type": ed.get("event_type"),
                "description": ed.get("description"),
                "technician_role": ed.get("technician_role"),
                "notes": ed.get("notes"),
                "timestamp": ts_str,
                "synthetic": ed.get("synthetic", True),
                "data_source": ed.get("data_source", "SYNTHETIC_DEMO"),
            })

    def _fmt_ts(val):
        if not val:
            return None
        return val.isoformat() if hasattr(val, "isoformat") else str(val)

    return {
        "service_job_id": sj["service_job_id"],
        "order_id": sj["order_id"],
        "shipment_id": sj.get("shipment_id"),
        "dealer_id": sj["dealer_id"],
        "dealer_name": d.get("dealer_name") or d.get("name") or sj["dealer_id"],
        "dealer_city": d.get("city"),
        "dealer_country": d.get("country"),
        "part_id": p.get("part_id"),
        "part_number": p.get("part_number"),
        "part_name": p.get("part_name"),
        "machine_id": m.get("machine_id"),
        "machine_model": m.get("model"),
        "status": sj["status"],
        "service_type": sj.get("service_type", "PARTS_INSTALLATION"),
        "work_order_number": sj.get("work_order_number"),
        "notes": sj.get("notes"),
        "received_at": _fmt_ts(sj.get("received_at")),
        "started_at": _fmt_ts(sj.get("started_at")),
        "installed_at": _fmt_ts(sj.get("installed_at")),
        "completed_at": _fmt_ts(sj.get("completed_at")),
        "cancelled_at": _fmt_ts(sj.get("cancelled_at")),
        "cancel_reason": sj.get("cancel_reason"),
        "synthetic": sj.get("synthetic", True),
        "data_source": sj.get("data_source", "SYNTHETIC_DEMO"),
        "external_job_id": sj.get("external_job_id"),
        "synced_at": _fmt_ts(sj.get("synced_at")),
        "provenance": sj.get("provenance", "INTERNAL_SERVICE_WORKFLOW"),
        "events": events,
    }


def get_service_job_by_order(session, order_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (o:Order {id: $order_id})-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
        RETURN sj.service_job_id AS id
        """,
        {"order_id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"No ServiceJob found for Order '{order_id}'")
    return get_service_job(session, row["id"])


def get_service_jobs_by_dealer(session, dealer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    rows = session.run(
        """
        MATCH (d:DealerBranch {dealer_id: $dealer_id})-[:PERFORMS_SERVICE]->(sj:ServiceJob)
        RETURN sj.service_job_id AS id
        ORDER BY sj.createdAt DESC
        LIMIT $limit
        """,
        {"dealer_id": dealer_id, "limit": limit},
    ).data()
    return [get_service_job(session, r["id"]) for r in rows]


def get_service_journey_trace(session, service_job_id: str) -> Dict[str, Any]:
    """
    Traverse the full end-to-end trace from Part -> Availability -> Fulfilment ->
    Allocation -> Order -> Shipment -> Dealer -> ServiceJob -> Events -> Close.
    """
    sj_data = get_service_job(session, service_job_id)
    order_id = sj_data["order_id"]

    trace_row = session.run(
        """
        MATCH (sj:ServiceJob {service_job_id: $id})
        OPTIONAL MATCH (o:Order {id: sj.order_id})
        OPTIONAL MATCH (sh:Shipment {shipment_id: sj.shipment_id})
        OPTIONAL MATCH (d:DealerBranch {dealer_id: sj.dealer_id})
        OPTIONAL MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        OPTIONAL MATCH (p:Part) WHERE p.part_id = sj.part_id OR p.part_number = o.partNumber
        OPTIONAL MATCH (m:Machine) WHERE m.machine_id = sj.machine_id
        RETURN o, sh, d, fr, p, m
        """,
        {"id": service_job_id},
    ).single()

    order = dict(trace_row["o"]) if trace_row and trace_row["o"] else {"id": order_id}
    shipment = dict(trace_row["sh"]) if trace_row and trace_row["sh"] else None
    dealer = dict(trace_row["d"]) if trace_row and trace_row["d"] else {"dealer_id": sj_data["dealer_id"]}
    fulfilment_req = dict(trace_row["fr"]) if trace_row and trace_row["fr"] else None
    part = dict(trace_row["p"]) if trace_row and trace_row["p"] else {"part_number": order.get("partNumber")}
    machine = dict(trace_row["m"]) if trace_row and trace_row["m"] else None

    # Construct complete chronological milestone list
    milestones = []
    if fulfilment_req:
        milestones.append({
            "stage": "FULFILMENT_REQUESTED",
            "status": fulfilment_req.get("status"),
            "timestamp": str(fulfilment_req.get("createdAt", "")),
            "label": "Part Requested & Fulfilment Sourced",
        })
    if order:
        milestones.append({
            "stage": "ORDER_CONFIRMED",
            "status": order.get("status"),
            "timestamp": str(order.get("createdAt", "")),
            "label": "OEM Parts Order Confirmed",
        })
    if shipment:
        milestones.append({
            "stage": "SHIPMENT_STATUS",
            "status": shipment.get("status"),
            "carrier": shipment.get("carrier"),
            "tracking_number": shipment.get("tracking_number"),
            "timestamp": str(shipment.get("shipped_at") or shipment.get("createdAt", "")),
            "label": f"Carrier Logistics ({shipment.get('status')})",
        })

    for ev in sj_data["events"]:
        milestones.append({
            "stage": f"SERVICE_{ev['event_type']}",
            "status": ev["event_type"],
            "description": ev["description"],
            "timestamp": ev["timestamp"],
            "technician_role": ev.get("technician_role"),
            "label": f"Dealer Service: {ev['event_type'].replace('_', ' ').title()}",
        })

    is_closed = (sj_data["status"] == "COMPLETED") and (
        not shipment or shipment.get("status") == "DELIVERED"
    )

    return {
        "service_job_id": service_job_id,
        "status": sj_data["status"],
        "part": {
            "part_id": part.get("part_id"),
            "part_number": part.get("part_number") or order.get("partNumber"),
            "part_name": part.get("part_name"),
            "category": part.get("part_category"),
        },
        "machine": {
            "machine_id": machine.get("machine_id"),
            "model": machine.get("model"),
            "category": machine.get("machine_category"),
        } if machine else None,
        "dealer": {
            "dealer_id": dealer.get("dealer_id"),
            "name": dealer.get("name"),
            "city": dealer.get("city"),
            "country": dealer.get("country"),
        },
        "order": {
            "order_id": order.get("id"),
            "status": order.get("status"),
            "quantity": order.get("quantity"),
            "total_price": order.get("totalPrice"),
        },
        "shipment": {
            "shipment_id": shipment.get("shipment_id"),
            "status": shipment.get("status"),
            "carrier": shipment.get("carrier"),
            "tracking_number": shipment.get("tracking_number"),
        } if shipment else None,
        "fulfilment_request": {
            "id": fulfilment_req.get("id"),
            "status": fulfilment_req.get("status"),
        } if fulfilment_req else None,
        "timeline_milestones": milestones,
        "is_closed": is_closed,
        "closed_at": sj_data.get("completed_at") if is_closed else None,
        "synthetic": True,
        "data_source": "SYNTHETIC_DEMO",
    }
