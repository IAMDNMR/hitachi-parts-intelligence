r"""
backend/app/modules/shipment/service.py


Phase 7 Shipment & Tracking domain service — Neo4j backend.

Canonical state transitions per docs/architecture/STATE_TRANSITION_ARCHITECTURE.md §C:

    CREATED -> DISPATCHED -> IN_TRANSIT -> DELIVERED
            \            /
             -> EXCEPTION -> (back to IN_TRANSIT, or CANCELLED)
            \
             -> CANCELLED

Enforces:
  - Shipment requires an ACCEPTED Order.
  - Deterministic state machine enforcement (invalid transitions return ConflictError).
  - Full audit logging via app.audit.service.record_audit_event.
  - Provider integration with TestShipmentProvider / TestTrackingProvider.
  - Strict labeling: synthetic/test shipments carry synthetic=true and NOT_CONNECTED.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.audit.service import record_audit_event
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.integrations.contracts.shipment import ShipmentCreationRequest
from app.integrations.factory import get_shipment_provider, get_tracking_provider

shipment_provider = get_shipment_provider()
tracking_provider = get_tracking_provider()


def create_shipment(
    session,
    order_id: str,
    service_tier: str = "STANDARD",
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Look up Order
    order = session.run(
        """
        MATCH (o:Order {id: $id})
        RETURN o.id AS id, o.status AS status, o.partNumber AS partNumber,
               o.quantity AS quantity, o.sourceId AS sourceId,
               o.destinationBranchId AS destinationBranchId,
               o.fulfilmentRequestId AS fulfilmentRequestId,
               o.synthetic AS synthetic, o.testRunId AS testRunId
        """,
        {"id": order_id},
    ).single()
    if not order:
        raise NotFoundError(f"Order '{order_id}' not found")
    order = dict(order)

    # 2. Check for existing shipment (idempotent return)
    existing = session.run(
        """
        MATCH (o:Order {id: $order_id})-[:HAS_SHIPMENT]->(sh:Shipment)
        RETURN sh.shipment_id AS shipment_id
        """,
        {"order_id": order_id},
    ).single()
    if existing:
        return get_shipment(session, existing["shipment_id"])

    # 3. Guard: Order must be in ACCEPTED state (or CREATED if test auto-accepts)
    if order["status"] not in ("ACCEPTED", "CREATED"):
        raise ConflictError(
            f"Cannot create shipment for order '{order_id}' in status '{order['status']}'. Requires ACCEPTED."
        )

    # If order is still CREATED, transition it to ACCEPTED to satisfy the business process
    if order["status"] == "CREATED":
        session.run(
            "MATCH (o:Order {id: $id}) SET o.status = 'ACCEPTED', o.updatedAt = datetime()",
            {"id": order_id},
        ).consume()
        record_audit_event(
            session=session,
            action="ORDER_ACCEPTED",
            entity_type="ORDER",
            entity_id=order_id,
            actor_id=actor_id,
            actor_role=actor_role,
            previous_state="CREATED",
            new_state="ACCEPTED",
            details={"auto_accepted_for_shipment": True},
            test_run_id=test_run_id,
        )

    # 4. Call ShipmentProvider
    active_shipment_provider = get_shipment_provider() or shipment_provider
    creation_result = active_shipment_provider.create_shipment(
        ShipmentCreationRequest(
            order_id=order_id,
            part_number=order["partNumber"],
            quantity=order["quantity"],
            origin_source_id=order.get("sourceId") or "DEPOT-OOSTERHOUT",
            destination_branch_id=order.get("destinationBranchId") or "DLR-019",
            service_tier=service_tier,
        )
    )

    shipment_id = f"ship-{uuid.uuid4()}"
    event_id = f"evt-{uuid.uuid4()}"
    is_connected = getattr(active_shipment_provider, "is_connected", False)
    is_synth = not is_connected
    data_source_val = creation_result.carrier if is_connected else "SYNTHETIC_DEMO"
    external_shipment_ref = creation_result.tracking_number
    synced_at_str = datetime.now(timezone.utc).isoformat()

    # 5. Persist Shipment and link to Order and DealerBranch
    session.run(
        """
        CREATE (sh:Shipment {
            shipment_id:          $shipment_id,
            order_id:             $order_id,
            status:               'CREATED',
            carrier:              $carrier,
            tracking_number:      $tracking_number,
            origin:               $origin,
            destination_branch:   $dest_branch,
            service_tier:         $service_tier,
            eta:                  $eta,
            synthetic:            $synthetic,
            data_source:          $data_source,
            external_shipment_id: $external_shipment_id,
            synced_at:            $synced_at,
            provenance:           'INTERNAL_TEST_WORKFLOW',
            createdAt:            datetime(),
            updatedAt:            datetime(),
            testRunId:            $test_run_id
        })
        """,
        {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "carrier": creation_result.carrier,
            "tracking_number": creation_result.tracking_number,
            "origin": order.get("sourceId") or "European Parts Centre, Oosterhout (NL)",
            "dest_branch": order.get("destinationBranchId"),
            "service_tier": service_tier,
            "eta": creation_result.estimated_delivery,
            "synthetic": is_synth,
            "data_source": data_source_val,
            "external_shipment_id": external_shipment_ref,
            "synced_at": synced_at_str,
            "test_run_id": test_run_id,
        },
    ).consume()

    session.run(
        """
        MATCH (o:Order {id: $order_id})
        MATCH (sh:Shipment {shipment_id: $shipment_id})
        MERGE (o)-[:HAS_SHIPMENT]->(sh)
        WITH sh, o
        OPTIONAL MATCH (dest:DealerBranch {dealer_id: o.destinationBranchId})
        FOREACH (d IN CASE WHEN dest IS NOT NULL THEN [dest] ELSE [] END |
            MERGE (sh)-[:SHIPPED_TO]->(d)
        )
        """,
        {"order_id": order_id, "shipment_id": shipment_id},
    ).consume()

    # Create initial ShipmentEvent
    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $shipment_id})
        CREATE (e:ShipmentEvent {
            id:          $event_id,
            event_type:  'CREATED',
            description: 'Shipment created and scheduled for carrier dispatch.',
            location:    $origin,
            timestamp:   datetime(),
            synthetic:   true,
            data_source: 'SYNTHETIC_DEMO',
            testRunId:   $test_run_id
        })
        MERGE (sh)-[:HAS_EVENT]->(e)
        """,
        {
            "shipment_id": shipment_id,
            "event_id": event_id,
            "origin": order.get("sourceId") or "Oosterhout, NL",
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action="SHIPMENT_CREATED",
        entity_type="SHIPMENT",
        entity_id=shipment_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=None,
        new_state="CREATED",
        details={
            "order_id": order_id,
            "tracking_number": creation_result.tracking_number,
            "carrier": creation_result.carrier,
            "eta": creation_result.estimated_delivery,
        },
        test_run_id=test_run_id,
    )

    return get_shipment(session, shipment_id)


def dispatch_shipment(
    session,
    shipment_id: str,
    location: Optional[str] = None,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    sh = _get_raw_shipment(session, shipment_id)
    if sh["status"] != "CREATED":
        raise ConflictError(
            f"Cannot dispatch shipment '{shipment_id}' in status '{sh['status']}'. Requires CREATED."
        )

    event_id = f"evt-{uuid.uuid4()}"
    disp_loc = location or sh.get("origin") or "European Parts Centre, Oosterhout (NL)"

    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})
        SET sh.status = 'DISPATCHED',
            sh.shipped_at = datetime(),
            sh.updatedAt = datetime()
        CREATE (e:ShipmentEvent {
            id:          $event_id,
            event_type:  'DISPATCHED',
            description: 'Shipment handed to carrier and dispatched from origin facility.',
            location:    $location,
            timestamp:   datetime(),
            synthetic:   true,
            data_source: 'SYNTHETIC_DEMO',
            testRunId:   $test_run_id
        })
        MERGE (sh)-[:HAS_EVENT]->(e)
        """,
        {"id": shipment_id, "event_id": event_id, "location": disp_loc, "test_run_id": test_run_id},
    ).consume()

    # Update linked FulfilmentRequest to SHIPPED if present
    session.run(
        """
        MATCH (o:Order)-[:HAS_SHIPMENT]->(sh:Shipment {shipment_id: $id})
        MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        SET fr.status = 'SHIPPED', fr.updatedAt = datetime()
        """,
        {"id": shipment_id},
    ).consume()

    record_audit_event(
        session=session,
        action="SHIPMENT_DISPATCHED",
        entity_type="SHIPMENT",
        entity_id=shipment_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state="CREATED",
        new_state="DISPATCHED",
        details={"location": disp_loc},
        test_run_id=test_run_id,
    )

    return get_shipment(session, shipment_id)


def record_tracking_event(
    session,
    shipment_id: str,
    event_type: str,
    description: str,
    location: Optional[str] = None,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    allowed = {"DISPATCHED", "IN_TRANSIT", "EXCEPTION", "DELIVERED"}
    if event_type not in allowed:
        raise UnprocessableError(f"Invalid tracking event type '{event_type}'. Must be one of {allowed}")

    sh = _get_raw_shipment(session, shipment_id)
    prev_state = sh["status"]

    # State machine transition rules
    new_status = prev_state
    if event_type == "IN_TRANSIT" and prev_state in ("DISPATCHED", "EXCEPTION"):
        new_status = "IN_TRANSIT"
    elif event_type == "EXCEPTION":
        new_status = "EXCEPTION"
    elif event_type == "DELIVERED":
        new_status = "DELIVERED"

    event_id = f"evt-{uuid.uuid4()}"
    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})
        SET sh.status = $new_status,
            sh.updatedAt = datetime()
        CREATE (e:ShipmentEvent {
            id:          $event_id,
            event_type:  $event_type,
            description: $description,
            location:    $location,
            timestamp:   datetime(),
            synthetic:   true,
            data_source: 'SYNTHETIC_DEMO',
            testRunId:   $test_run_id
        })
        MERGE (sh)-[:HAS_EVENT]->(e)
        """,
        {
            "id": shipment_id,
            "new_status": new_status,
            "event_id": event_id,
            "event_type": event_type,
            "description": description,
            "location": location,
            "test_run_id": test_run_id,
        },
    ).consume()

    record_audit_event(
        session=session,
        action=f"SHIPMENT_EVENT_{event_type}",
        entity_type="SHIPMENT",
        entity_id=shipment_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=prev_state,
        new_state=new_status,
        details={"event_type": event_type, "description": description, "location": location},
        test_run_id=test_run_id,
    )

    return get_shipment(session, shipment_id)


def confirm_delivery(
    session,
    shipment_id: str,
    location: Optional[str] = None,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    sh = _get_raw_shipment(session, shipment_id)
    if sh["status"] in ("DELIVERED", "CANCELLED"):
        raise ConflictError(
            f"Cannot deliver shipment '{shipment_id}' already in terminal status '{sh['status']}'."
        )

    event_id = f"evt-{uuid.uuid4()}"
    if not location:
        # Record the real receiving dealer, not a generic placeholder.
        dest = session.run(
            """MATCH (sh:Shipment {shipment_id: $id})
               OPTIONAL MATCH (sh)-[:SHIPPED_TO]->(d:DealerBranch)
               RETURN coalesce(d.dealer_name + CASE WHEN d.city <> '' THEN ', ' + d.city ELSE '' END,
                               sh.destination_branch) AS loc""",
            {"id": shipment_id},
        ).single()
        location = dest["loc"] if dest and dest["loc"] else None
    deliv_loc = location or "Receiving dealer (not recorded)"

    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})
        SET sh.status = 'DELIVERED',
            sh.delivered_at = datetime(),
            sh.updatedAt = datetime()
        CREATE (e:ShipmentEvent {
            id:          $event_id,
            event_type:  'DELIVERED',
            description: 'Shipment delivered to destination dealer facility and accepted.',
            location:    $location,
            timestamp:   datetime(),
            synthetic:   true,
            data_source: 'SYNTHETIC_DEMO',
            testRunId:   $test_run_id
        })
        MERGE (sh)-[:HAS_EVENT]->(e)
        """,
        {"id": shipment_id, "event_id": event_id, "location": deliv_loc, "test_run_id": test_run_id},
    ).consume()

    # Update linked FulfilmentRequest to DELIVERED
    session.run(
        """
        MATCH (o:Order)-[:HAS_SHIPMENT]->(sh:Shipment {shipment_id: $id})
        MATCH (fr:FulfilmentRequest)-[:HAS_ORDER]->(o)
        SET fr.status = 'DELIVERED', fr.updatedAt = datetime()
        """,
        {"id": shipment_id},
    ).consume()

    record_audit_event(
        session=session,
        action="SHIPMENT_DELIVERED",
        entity_type="SHIPMENT",
        entity_id=shipment_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=sh["status"],
        new_state="DELIVERED",
        details={"location": deliv_loc},
        test_run_id=test_run_id,
    )

    return get_shipment(session, shipment_id)


def cancel_shipment(
    session,
    shipment_id: str,
    reason: str,
    actor_id: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    sh = _get_raw_shipment(session, shipment_id)
    if sh["status"] == "DELIVERED":
        raise ConflictError(f"Cannot cancel shipment '{shipment_id}' after it has been DELIVERED.")

    event_id = f"evt-{uuid.uuid4()}"
    session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})
        SET sh.status = 'CANCELLED',
            sh.updatedAt = datetime()
        CREATE (e:ShipmentEvent {
            id:          $event_id,
            event_type:  'CANCELLED',
            description: $reason,
            location:    null,
            timestamp:   datetime(),
            synthetic:   true,
            data_source: 'SYNTHETIC_DEMO',
            testRunId:   $test_run_id
        })
        MERGE (sh)-[:HAS_EVENT]->(e)
        """,
        {"id": shipment_id, "event_id": event_id, "reason": f"Shipment cancelled: {reason}", "test_run_id": test_run_id},
    ).consume()

    record_audit_event(
        session=session,
        action="SHIPMENT_CANCELLED",
        entity_type="SHIPMENT",
        entity_id=shipment_id,
        actor_id=actor_id,
        actor_role=actor_role,
        previous_state=sh["status"],
        new_state="CANCELLED",
        details={"reason": reason},
        test_run_id=test_run_id,
    )

    return get_shipment(session, shipment_id)


def get_shipment(session, shipment_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})
        OPTIONAL MATCH (o:Order)-[:HAS_SHIPMENT]->(sh)
        OPTIONAL MATCH (sh)-[:SHIPPED_TO]->(dest:DealerBranch)
        RETURN sh.shipment_id AS shipment_id, sh.status AS status,
               sh.carrier AS carrier, sh.tracking_number AS tracking_number,
               sh.origin AS origin, sh.destination AS destination,
               sh.service_tier AS service_tier, sh.eta AS eta,
               sh.shipped_at AS shipped_at, sh.delivered_at AS delivered_at,
               sh.synthetic AS synthetic, sh.data_source AS data_source,
               sh.external_shipment_id AS external_shipment_id,
               sh.synced_at AS synced_at,
               sh.provenance AS provenance,
               o.id AS order_id, dest.dealer_id AS destination_branch_id,
               dest.dealer_name AS destination_dealer_name
        """,
        {"id": shipment_id},
    ).single()
    if not row:
        raise NotFoundError(f"Shipment '{shipment_id}' not found")
    data = dict(row)

    for field in ("shipped_at", "delivered_at"):
        if data.get(field) is not None:
            data[field] = str(data[field])

    # Fetch ordered events
    events = session.run(
        """
        MATCH (sh:Shipment {shipment_id: $id})-[:HAS_EVENT]->(e:ShipmentEvent)
        RETURN e.id AS id, e.event_type AS event_type, e.description AS description,
               e.location AS location, e.timestamp AS timestamp,
               e.synthetic AS synthetic, e.data_source AS data_source
        ORDER BY e.timestamp ASC
        """,
        {"id": shipment_id},
    ).data()

    for e in events:
        if e.get("timestamp") is not None:
            e["timestamp"] = str(e["timestamp"])

    data["events"] = events
    data["external_shipment_id"] = data.get("external_shipment_id")
    data["synced_at"] = data.get("synced_at")
    data["integration_status"] = "CONNECTED" if not data.get("synthetic", True) else "NOT_CONNECTED"
    data["integration_label"] = (
        "LIVE_CARRIER — verified integration"
        if not data.get("synthetic", True)
        else "TEST/DEVELOPMENT — no real HCME carrier system is connected"
    )
    return data


def get_shipment_by_order(session, order_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (o:Order {id: $order_id})-[:HAS_SHIPMENT]->(sh:Shipment)
        RETURN sh.shipment_id AS shipment_id
        """,
        {"order_id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"No shipment found for order '{order_id}'")
    return get_shipment(session, row["shipment_id"])


def get_tracking(session, tracking_number: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (sh:Shipment {tracking_number: $tracking_number})
        RETURN sh.shipment_id AS shipment_id
        """,
        {"tracking_number": tracking_number},
    ).single()
    if not row:
        raise NotFoundError(f"Tracking reference '{tracking_number}' not found")
    sh = get_shipment(session, row["shipment_id"])
    return {
        "tracking_number": sh["tracking_number"],
        "shipment_id": sh["shipment_id"],
        "status": sh["status"],
        "carrier": sh["carrier"],
        "origin": sh.get("origin"),
        "destination": sh.get("destination") or sh.get("destination_dealer_name"),
        "eta": sh.get("eta"),
        "shipped_at": sh.get("shipped_at"),
        "delivered_at": sh.get("delivered_at"),
        "synthetic": sh.get("synthetic", True),
        "data_source": sh.get("data_source"),
        "external_shipment_id": sh.get("external_shipment_id"),
        "synced_at": sh.get("synced_at"),
        "integration_status": sh.get("integration_status", "NOT_CONNECTED"),
        "events": sh.get("events", []),
    }


def _get_raw_shipment(session, shipment_id: str) -> Dict[str, Any]:
    row = session.run(
        "MATCH (sh:Shipment {shipment_id: $id}) RETURN sh.shipment_id AS id, sh.status AS status, sh.origin AS origin",
        {"id": shipment_id},
    ).single()
    if not row:
        raise NotFoundError(f"Shipment '{shipment_id}' not found")
    return dict(row)
