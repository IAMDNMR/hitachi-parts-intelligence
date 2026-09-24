"""
backend/app/modules/order/lifecycle.py

Customer order placement and the business (operations) lifecycle, all persisted in the existing Neo4j AuraDB.

  Customer:   Customer details -> Cart -> Delivery -> Availability -> Fulfilment -> Review -> PLACE ORDER -> Confirmation
  Operations: Order -> Allocation -> Fulfilment -> Shipment -> Tracking -> Dealer Service -> Completed

There is no second order model: the (:Order) node written here is the same node the allocation, shipment and service modules already read, and every
operations step calls the existing service function (create_allocation, create_shipment, dispatch_shipment, record_tracking_event, confirm_delivery,
create_service_job, ...). The lifecycle position is *derived from the graph* (allocation / shipment / service-job nodes), never held in memory.

Order IDs are HCME-ORD-000123, taken from a counter node in the same database, so they are unique and survive restarts.
Everything remains SYNTHETIC_DEMO: no ERP, carrier, TMS or dealer system is connected.
"""

from typing import Any, Dict, List, Optional

from app.audit.service import record_audit_event
from app.errors.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.integrations.contracts.order import OrderSubmission
from app.integrations.contracts.pricing import PricingQuery
from app.modules.allocation.service import create_allocation, get_allocation, is_demo_part_number, release_allocation
from app.modules.order.service import advance_order_state, cancel_order, get_order, order_provider, pricing_provider
from app.modules.service.service import (
    complete_service,
    create_service_job,
    install_part,
    receive_part,
    start_service,
)
from app.modules.shipment.service import (
    confirm_delivery,
    create_shipment,
    dispatch_shipment,
    get_shipment,
    record_tracking_event,
)

ORDER_ID_PREFIX = "HCME-ORD-"

# The business lifecycle, in order. `key` is the step; each is derived from persisted graph state.
STEPS = [
    ("order", "Order"),
    ("allocation", "Allocation"),
    ("fulfilment", "Fulfilment"),
    ("shipment", "Shipment"),
    ("tracking", "Tracking"),
    ("service", "Dealer Service"),
    ("completed", "Completed"),
]


def _next_order_id(session) -> str:
    n = session.run(
        """
        MERGE (c:Counter {name: 'HCME_ORDER'})
        ON CREATE SET c.value = 0
        SET c.value = c.value + 1
        RETURN c.value AS n
        """
    ).single()["n"]
    return f"{ORDER_ID_PREFIX}{int(n):06d}"


def place_order(
    session,
    fulfilment_request_id: str,
    customer: Dict[str, Optional[str]],
    part_name: Optional[str] = None,
    actor_id: str = "CUSTOMER",
    actor_role: str = "CUSTOMER",
    test_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist the customer's order. Idempotent per fulfilment request (a second call returns the same Order)."""
    existing = session.run(
        "MATCH (:FulfilmentRequest {id: $id})-[:HAS_ORDER]->(o:Order) RETURN o.id AS id", {"id": fulfilment_request_id}
    ).single()
    if existing:
        return get_order_details(session, existing["id"])

    req = session.run(
        """
        MATCH (r:FulfilmentRequest {id: $id})
        RETURN r.id AS id, r.status AS status, r.partNumber AS partNumber, r.quantity AS quantity,
               r.destinationBranchId AS dest, r.selectedOptionId AS optId, r.machineContext AS machine
        """,
        {"id": fulfilment_request_id},
    ).single()
    if not req:
        raise NotFoundError(f"Fulfilment request '{fulfilment_request_id}' not found")
    req = dict(req)
    if req["status"] != "ALLOCATION_PENDING":
        raise ConflictError(
            f"Cannot place an order for a request in status '{req['status']}'. It must have an availability check and a selected fulfilment option."
        )
    name = (customer.get("name") or "").strip()
    email = (customer.get("email") or "").strip()
    if not name or not email:
        raise UnprocessableError("Customer name and email are required to place an order.")

    part = session.run(
        "MATCH (p:Part {part_number: $pn}) RETURN p.part_id AS part_id, p.part_name AS name", {"pn": req["partNumber"]}
    ).single()
    if not part and not is_demo_part_number(req["partNumber"]):
        raise NotFoundError(f"Part '{req['partNumber']}' not found (canonical Part must exist)")
    resolved_name = (part["name"] if part and part["name"] else None) or part_name

    dealer = session.run(
        """
        MATCH (d:DealerBranch {dealer_id: $id})
        RETURN d.dealer_id AS id, d.dealer_name AS name, d.address AS address, d.city AS city, d.country AS country
        """,
        {"id": req["dest"]},
    ).single()
    dealer = dict(dealer) if dealer else {"id": req["dest"], "name": None, "address": None, "city": None, "country": None}

    opt = session.run(
        """
        MATCH (o:FulfilmentOption {id: $id})
        RETURN o.transportMode AS mode, o.serviceLevel AS service, o.carrierCode AS carrier, o.transitDays AS days,
               o.eta AS eta, o.transportCost AS cost, o.currency AS currency, o.sourceId AS sourceId
        """,
        {"id": req["optId"]},
    ).single()
    opt = dict(opt) if opt else {}

    quote = pricing_provider.get_price(PricingQuery(part_number=req["partNumber"], quantity=int(req["quantity"] or 1)))
    order_id = _next_order_id(session)

    cypher = """
        MATCH (r:FulfilmentRequest {id: $req_id})
        CREATE (o:Order {
            id: $id, fulfilmentRequestId: $req_id,
            customerName: $cname, customerEmail: $cemail, customerPhone: $cphone, customerCompany: $ccompany,
            shipToDealerId: $dealer_id, shipToDealerName: $dealer_name, shipToAddress: $dealer_address,
            shipToCity: $dealer_city, shipToCountry: $dealer_country,
            partNumber: $part_number, partName: $part_name, quantity: $quantity, machineContext: $machine,
            destinationBranchId: $dealer_id, sourceId: $source_id,
            fulfilmentOptionId: $opt_id, fulfilmentMode: $mode, fulfilmentServiceLevel: $service, fulfilmentCarrier: $carrier,
            fulfilmentTransitDays: $days, fulfilmentEta: $eta, fulfilmentCost: $cost, fulfilmentCurrency: $currency,
            unitPrice: $unit_price, currency: $price_currency, pricingStatus: $pricing_status,
            status: 'CREATED', provenance: 'SYNTHETIC_DEMO_WORKFLOW', data_source: 'SYNTHETIC_DEMO', synthetic: true,
            placedAt: datetime(), createdAt: datetime(), updatedAt: datetime()
        })
        MERGE (r)-[:HAS_ORDER]->(o)
        WITH o
        OPTIONAL MATCH (p:Part {part_number: $part_number})
        FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END | MERGE (o)-[:FOR_PART]->(p))
        WITH o
        OPTIONAL MATCH (d:DealerBranch {dealer_id: $dealer_id})
        FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END | MERGE (o)-[:DESTINED_FOR]->(d))
        RETURN o.id AS id
    """
    params = {
        "id": order_id, "req_id": fulfilment_request_id,
        "cname": name, "cemail": email, "cphone": (customer.get("phone") or "").strip() or None,
        "ccompany": (customer.get("company") or "").strip() or None,
        "dealer_id": dealer["id"], "dealer_name": dealer["name"], "dealer_address": dealer["address"],
        "dealer_city": dealer["city"], "dealer_country": dealer["country"],
        "part_number": req["partNumber"], "part_name": resolved_name, "quantity": int(req["quantity"] or 1),
        "machine": req["machine"], "source_id": opt.get("sourceId"),
        "opt_id": req["optId"], "mode": opt.get("mode"), "service": opt.get("service"), "carrier": opt.get("carrier"),
        "days": opt.get("days"), "eta": opt.get("eta"), "cost": opt.get("cost"), "currency": opt.get("currency"),
        "unit_price": quote.unit_price, "price_currency": quote.currency, "pricing_status": quote.status,
    }
    if test_run_id:
        cypher = cypher.replace("RETURN o.id AS id", "SET o.testRunId = $test_run_id RETURN o.id AS id")
        params["test_run_id"] = test_run_id
    session.run(cypher, params).consume()

    record_audit_event(
        session=session, action="ORDER_PLACED", entity_type="ORDER", entity_id=order_id, actor_id=actor_id, actor_role=actor_role,
        previous_state=None, new_state="CREATED",
        details={"fulfilment_request_id": fulfilment_request_id, "part_number": req["partNumber"], "quantity": req["quantity"],
                 "dealer_id": dealer["id"], "fulfilment_option_id": req["optId"]},
        test_run_id=test_run_id,
    )
    return get_order_details(session, order_id)


_DETAIL_Q = """
MATCH (o:Order {id: $id})
RETURN o.id AS order_id, o.status AS status, o.fulfilmentRequestId AS fulfilment_request_id,
       o.customerName AS customer_name, o.customerEmail AS customer_email, o.customerPhone AS customer_phone,
       o.customerCompany AS customer_company,
       o.shipToDealerId AS dealer_id, o.shipToDealerName AS dealer_name, o.shipToAddress AS ship_to_address,
       o.shipToCity AS ship_to_city, o.shipToCountry AS ship_to_country,
       o.partNumber AS part_number, o.partName AS part_name, o.quantity AS quantity, o.machineContext AS machine_context,
       o.fulfilmentOptionId AS fulfilment_option_id, o.fulfilmentMode AS fulfilment_mode,
       o.fulfilmentServiceLevel AS fulfilment_service_level, o.fulfilmentTransitDays AS fulfilment_transit_days,
       o.fulfilmentEta AS fulfilment_eta, o.fulfilmentCost AS fulfilment_cost, o.fulfilmentCurrency AS fulfilment_currency,
       o.pricingStatus AS pricing_status, o.data_source AS data_source, o.provenance AS provenance,
       toString(o.placedAt) AS placed_at, toString(o.updatedAt) AS updated_at
"""


def get_order_details(session, order_id: str) -> Dict[str, Any]:
    row = session.run(_DETAIL_Q, {"id": order_id}).single()
    if not row:
        raise NotFoundError(f"Order '{order_id}' not found")
    d = dict(row)
    d["parts"] = [{"part_number": d["part_number"], "part_name": d["part_name"], "quantity": d["quantity"]}]
    d["integration_label"] = "SYNTHETIC_DEMO — no real HCME ERP, carrier, TMS or dealer system is connected"
    return d


def list_orders(session, limit: int = 200) -> List[Dict[str, Any]]:
    rows = session.run(
        """
        MATCH (o:Order) WHERE o.customerName IS NOT NULL
        RETURN o.id AS order_id, o.status AS status, o.customerName AS customer_name, o.shipToDealerName AS dealer_name,
               o.partNumber AS part_number, o.partName AS part_name, o.quantity AS quantity, toString(o.placedAt) AS placed_at,
               o.data_source AS data_source, o.provenance AS provenance
        ORDER BY o.placedAt DESC LIMIT $limit
        """,
        {"limit": limit},
    ).data()
    for r in rows:
        r["parts"] = [{"part_number": r["part_number"], "part_name": r["part_name"], "quantity": r["quantity"]}]
    return rows


def _links(session, order_id: str) -> Dict[str, Any]:
    row = session.run(
        """
        MATCH (o:Order {id: $id})
        OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
        OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
        OPTIONAL MATCH (o)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
        RETURN o.status AS order_status, o.fulfilmentRequestId AS req_id,
               a.id AS allocation_id, a.status AS allocation_status,
               sh.shipment_id AS shipment_id, sh.status AS shipment_status,
               sj.service_job_id AS service_job_id, sj.status AS service_job_status
        """,
        {"id": order_id},
    ).single()
    if not row:
        raise NotFoundError(f"Order '{order_id}' not found")
    return dict(row)


def _next_action(k: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """The single next operations action, from persisted state."""
    if k["order_status"] == "CANCELLED":
        return None
    if not k["allocation_id"]:
        return {"key": "allocate", "label": "Allocate inventory"}
    if k["order_status"] == "CREATED":
        return {"key": "fulfil", "label": "Confirm fulfilment"}
    if not k["shipment_id"]:
        return {"key": "create_shipment", "label": "Create shipment"}
    sh = k["shipment_status"]
    if sh == "CREATED":
        return {"key": "dispatch", "label": "Dispatch shipment"}
    if sh == "DISPATCHED":
        return {"key": "in_transit", "label": "Record in-transit tracking event"}
    if sh in ("IN_TRANSIT", "EXCEPTION"):
        return {"key": "deliver", "label": "Confirm delivery"}
    if not k["service_job_id"]:
        return {"key": "create_service_job", "label": "Create dealer service job"}
    sj = k["service_job_status"]
    return {
        "OPEN": {"key": "receive", "label": "Record part received at dealer"},
        "PART_RECEIVED": {"key": "start", "label": "Start service work"},
        "IN_PROGRESS": {"key": "install", "label": "Record installation"},
        "PART_INSTALLED": {"key": "complete", "label": "Complete service"},
    }.get(sj)


def get_operations(session, order_id: str) -> Dict[str, Any]:
    """Order + its lifecycle steps, derived entirely from what is stored in the graph."""
    order = get_order_details(session, order_id)
    k = _links(session, order_id)
    shipment = get_shipment(session, k["shipment_id"]) if k["shipment_id"] else None
    done_alloc = k["allocation_status"] in ("CONFIRMED", "CONSUMED")
    done_fulfil = k["order_status"] in ("ACCEPTED", "FULFILLED", "CLOSED")
    ship_status = k["shipment_status"]
    delivered = ship_status == "DELIVERED"
    service_done = k["service_job_status"] == "COMPLETED"
    state = {
        "order": "done",
        "allocation": "done" if done_alloc else "current",
        "fulfilment": "done" if done_fulfil else ("current" if done_alloc else "pending"),
        "shipment": "done" if k["shipment_id"] else ("current" if done_fulfil else "pending"),
        "tracking": "done" if delivered else ("current" if k["shipment_id"] else "pending"),
        "service": "done" if service_done else ("current" if delivered else "pending"),
        "completed": "done" if service_done else "pending",
    }
    detail = {
        "allocation": k["allocation_status"],
        "shipment": ship_status,
        "tracking": ship_status if k["shipment_id"] else None,
        "service": k["service_job_status"],
    }
    action = _next_action(k)
    return {
        "order": order,
        "steps": [{"key": key, "label": label, "state": state[key], "detail": detail.get(key)} for key, label in STEPS],
        "next_action": action,
        "allocation_id": k["allocation_id"],
        "shipment": shipment,
        "service_job_id": k["service_job_id"],
        "service_job_status": k["service_job_status"],
        "order_status": k["order_status"],
        "completed": service_done,
        "cancelled": k["order_status"] == "CANCELLED",
        "can_cancel": _can_cancel(k),
        "integration_label": order["integration_label"],
    }


def run_action(session, order_id: str, action: str, actor_id: str = "OPERATIONS", actor_role: str = "OPERATIONS",
               test_run_id: Optional[str] = None) -> Dict[str, Any]:
    """Perform one operations step by calling the existing service, but only if it is the order's next action."""
    k = _links(session, order_id)
    if action == "cancel":
        return _cancel(session, order_id, k, actor_id, actor_role, test_run_id)
    nxt = _next_action(k)
    if not nxt or nxt["key"] != action:
        raise ConflictError(
            f"'{action}' is not the next step for order {order_id}"
            + (f" (next: {nxt['key']})." if nxt else " (the order has no further steps).")
        )
    ident = {"actor_id": actor_id, "actor_role": actor_role, "test_run_id": test_run_id}

    if action == "allocate":
        alloc = create_allocation(session=session, fulfilment_request_id=k["req_id"], idempotency_key=f"alloc-{order_id}", **ident)
        session.run(
            """
            MATCH (o:Order {id: $id}), (a:Allocation {id: $aid})
            MERGE (o)-[:BASED_ON_ALLOCATION]->(a)
            SET o.sourceId = $source, o.allocatedAt = datetime(), o.updatedAt = datetime()
            """,
            {"id": order_id, "aid": alloc["allocation_id"], "source": alloc["source_id"]},
        ).consume()
    elif action == "fulfil":
        _confirm_fulfilment(session, order_id, k["req_id"], **ident)
    elif action == "create_shipment":
        create_shipment(session, order_id, service_tier="STANDARD", **ident)
    elif action == "dispatch":
        dispatch_shipment(session, k["shipment_id"], **ident)
    elif action == "in_transit":
        record_tracking_event(session, k["shipment_id"], "IN_TRANSIT", "Shipment in transit (simulated tracking event)", **ident)
    elif action == "deliver":
        confirm_delivery(session, k["shipment_id"], **ident)
    elif action == "create_service_job":
        create_service_job(session, order_id, **ident)
    elif action == "receive":
        receive_part(session, k["service_job_id"], **ident)
    elif action == "start":
        start_service(session, k["service_job_id"], **ident)
    elif action == "install":
        install_part(session, k["service_job_id"], **ident)
    elif action == "complete":
        complete_service(session, k["service_job_id"], **ident)
    if action in ("deliver", "complete"):
        # delivery moves the order to FULFILLED, a completed service job closes it (the existing state machine); persisted on the Order
        advance_order_state(session, order_id, actor_id=actor_id, actor_role=actor_role, test_run_id=test_run_id)
    return get_operations(session, order_id)


def _can_cancel(k: Dict[str, Any]) -> bool:
    """An order can be cancelled until its shipment is dispatched."""
    return k["order_status"] in ("CREATED", "ACCEPTED") and k["shipment_status"] in (None, "CREATED")


def _cancel(session, order_id: str, k: Dict[str, Any], actor_id: str, actor_role: str, test_run_id: Optional[str]) -> Dict[str, Any]:
    if not _can_cancel(k):
        raise ConflictError(f"Order {order_id} can no longer be cancelled (status {k['order_status']}, shipment {k['shipment_status'] or 'none'}).")
    if k["allocation_status"] == "CONFIRMED":
        release_allocation(session, k["req_id"], actor_id=actor_id, actor_role=actor_role, test_run_id=test_run_id)  # give the reserved stock back
    cancel_order(session, order_id, reason="Cancelled by operations", actor_id=actor_id, actor_role=actor_role, test_run_id=test_run_id)
    return get_operations(session, order_id)


def _confirm_fulfilment(session, order_id: str, req_id: str, actor_id: str, actor_role: str, test_run_id: Optional[str]) -> None:
    """Fulfilment: consume the allocation, submit the order to the (simulated) order provider, and mark the order ACCEPTED."""
    o = get_order(session, order_id)
    alloc = get_allocation(session, req_id)
    if alloc["status"] != "CONFIRMED":
        raise ConflictError(f"Cannot confirm fulfilment: allocation is '{alloc['status']}', requires CONFIRMED.")
    session.run(
        """
        MATCH (a:Allocation {id: $aid}), (r:FulfilmentRequest {id: $req})
        SET a.status = 'CONSUMED', r.status = 'ORDERED', r.updatedAt = datetime()
        """,
        {"aid": alloc["id"], "req": req_id},
    ).consume()
    result = order_provider.submit_order(
        OrderSubmission(order_id=order_id, part_number=o["partNumber"], quantity=o["quantity"],
                        source_id=alloc["sourceId"], destination_branch_id=o["destinationBranchId"])
    )
    data_source = "HCME_SAP_ERP" if result.accepted else "SYNTHETIC_DEMO"
    session.run(
        """
        MATCH (o:Order {id: $id})
        SET o.external_order_id = $ext, o.synced_at = $synced, o.data_source = $ds, o.synthetic = ($ds = 'SYNTHETIC_DEMO'),
            o.status = 'ACCEPTED', o.fulfilmentConfirmedAt = datetime(), o.updatedAt = datetime()
        """,
        {"id": order_id, "ext": result.external_order_reference, "synced": _now_iso(), "ds": data_source},
    ).consume()
    record_audit_event(
        session=session, action="ORDER_ACCEPTED", entity_type="ORDER", entity_id=order_id, actor_id=actor_id, actor_role=actor_role,
        previous_state="CREATED", new_state="ACCEPTED",
        details={"provider_status": result.status, "allocation_id": alloc["id"]}, test_run_id=test_run_id,
    )


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
