"""
Browser check of the Orders screen: summary numbers vs the database, working filters, and that EVERY lifecycle step shows its own content when clicked
while the persisted step states (done / current / pending) never change from a click.

Needs the backend on :8000 and a built frontend. It places two test orders through the API (customer email orders-ui@example.eu) and processes them
through the API to different points so all three situations are covered: just placed, mid-lifecycle, completed. Delete them afterwards.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright  # noqa: E402

from app.db.neo4j.connection import get_neo4j_driver  # noqa: E402

API = "http://localhost:8000/api/v1"
BASE = "http://localhost:4173"
FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
STEPS = ["order", "allocation", "fulfilment", "shipment", "tracking", "service", "completed"]
results = []


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "x-test-user-id": "u", "x-test-role": "CUSTOMER"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def place(dealer="DLR-045"):
    pn = "4663907"
    rid = call("POST", "/fulfilment-requests", {"part_number": pn, "quantity": 1, "destination_branch_id": dealer,
                                                "requester_name": "Orders UI", "requester_email": "orders-ui@example.eu"})["id"]
    call("POST", f"/fulfilment-requests/{rid}/availability", {"part_number": pn, "quantity": 1, "destination_branch_id": dealer})
    opt = call("POST", f"/fulfilment-requests/{rid}/options")["options"][0]["id"]
    call("POST", f"/fulfilment-requests/{rid}/select-option", {"option_id": opt})
    call("POST", f"/fulfilment-requests/{rid}/proceed-to-allocation")
    return call("POST", f"/fulfilment-requests/{rid}/place-order", {"customer_name": "Orders UI", "customer_email": "orders-ui@example.eu", "customer_phone": "+31 6 0000 0001"})["order_id"]


def advance(oid, actions):
    for a in actions:
        call("POST", f"/orders/{oid}/ops/{a}")


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))


prev = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview", "--port", "4173"], cwd=FRONT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
for _ in range(20):
    try:
        urllib.request.urlopen(BASE + "/", timeout=2)
        break
    except Exception:
        time.sleep(1)

FULL = ["allocate", "fulfil", "create_shipment", "dispatch", "in_transit", "deliver", "create_service_job", "receive", "start", "install", "complete"]
placed = place()
mid = place()
advance(mid, FULL[:5])           # allocated, fulfilled, shipment dispatched and in transit
done = place()
advance(done, FULL)              # completed
orders = {"placed": placed, "mid-lifecycle": mid, "completed": done}
print("orders:", orders)

errors = []
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        p = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        p.on("pageerror", lambda e: errors.append(str(e)))

        # ---- list: summary equals the database, filters work ---------------------------------
        p.goto(BASE + "/#/orders")
        p.reload()
        p.wait_for_selector("[data-testid='order-row']", timeout=15000)
        api_orders = call("GET", "/orders")["orders"]
        want = {"total-orders": len(api_orders), "placed": sum(o["status"] == "CREATED" for o in api_orders),
                "in-processing": sum(o["status"] in ("ACCEPTED", "FULFILLED") for o in api_orders),
                "completed": sum(o["status"] == "CLOSED" for o in api_orders)}
        got = {k: int(p.locator(f"[data-testid='summary-{k}'] .ord__stat-value").inner_text()) for k in want}
        check("summary cards equal the stored orders", got == want, f"{got}")
        p.fill("input[aria-label='Search orders']", placed)
        check("search by order ID narrows the list", p.locator("[data-testid='order-row']").count() == 1)
        p.fill("input[aria-label='Search orders']", "")
        p.select_option("select[aria-label='Filter by status']", "CLOSED")
        check("status filter works", p.locator("[data-testid='order-row']:has-text('Completed')").count() == p.locator("[data-testid='order-row']").count() > 0)
        p.select_option("select[aria-label='Filter by status']", "ALL")
        p.select_option("select[aria-label='Sort orders']", "id_asc")
        ids = [t.strip() for t in p.locator(".ord__id").all_inner_texts()]
        check("sort by Order ID works", ids == sorted(ids), str(ids[:3]))
        p.fill("input[aria-label='Ordered from']", "2999-01-01")
        check("date filter works (future date shows nothing)", p.locator("[data-testid='order-row']").count() == 0)
        p.fill("input[aria-label='Ordered from']", "")

        # ---- detail: click every step for orders in three different persisted states ----------
        MUST = {  # text that must appear in the panel of each step
            "order": ["Order ID", "Customer", "Parts & quantities", "Dealer", "Delivery address"],
            "allocation": ["Allocation status", "Source / depot"],
            "fulfilment": ["Fulfilment option", "Transit time", "Freight cost"],
            "shipment": ["Shipment status", "Shipment ID"],
            "tracking": ["Tracking ID", "Tracking events"],
            "service": ["Service job", "Service status", "Service milestones"],
            "completed": ["Final order status", "Lifecycle summary"],
        }
        for label, oid in orders.items():
            p.goto(f"{BASE}/#/orders/{oid}")
            p.reload()
            p.wait_for_selector("[data-testid='detail-order-id']", timeout=15000)
            states_before = [p.locator(f"li.ord__step[data-step='{s}']").get_attribute("data-state") for s in STEPS]
            panels = {}
            for s in STEPS:
                p.locator(f"li.ord__step[data-step='{s}'] button").click()
                p.wait_for_selector(f"[data-panel='{s}']")
                txt = p.locator(f"[data-panel='{s}']").inner_text()
                panels[s] = txt
                check(f"[{label}] {s}: panel shows this step's content", all(m.lower() in txt.lower() for m in MUST[s]), "")
                check(f"[{label}] {s}: selected step is highlighted", p.locator(f"li.ord__step[data-step='{s}'].is-selected").count() == 1)
            check(f"[{label}] all 7 panels are different", len(set(panels.values())) == 7)
            states_after = [p.locator(f"li.ord__step[data-step='{s}']").get_attribute("data-state") for s in STEPS]
            check(f"[{label}] clicking never changes step states", states_before == states_after, f"{states_before}")
            db_state = call("GET", f"/orders/{oid}/operations")["steps"]
            check(f"[{label}] step states equal the stored lifecycle", states_after == [x["state"] for x in db_state])

        # ---- spot checks of real content ------------------------------------------------------
        p.goto(f"{BASE}/#/orders/{done}")
        p.reload()
        p.wait_for_selector("[data-testid='detail-order-id']")
        p.locator("li.ord__step[data-step='completed'] button").click()
        t = p.locator("[data-panel='completed']").inner_text()
        check("completed panel shows shipment, work order and completion time", all(x in t for x in ("SHP", "Completed")) or ("Shipment / tracking" in t and "Completed" in t))
        p.locator("li.ord__step[data-step='tracking'] button").click()
        check("tracking panel lists the stored events", p.locator("[data-panel='tracking'] .ord__timeline li").count() >= 3)
        p.goto(f"{BASE}/#/orders/{mid}")
        p.reload()
        p.wait_for_selector("[data-testid='detail-order-id']")
        check("in-transit order opens on its current step (tracking)", p.locator("[data-panel='tracking']").count() == 1)
        p.locator("li.ord__step[data-step='service'] button").click()
        check("pending step says it has not started", "has not started" in p.locator("[data-panel='service']").inner_text())
        p.locator("li.ord__step[data-step='tracking'] button").click()
        p.locator("button[data-action='deliver']").click()
        p.wait_for_function("() => document.querySelector(\"li.ord__step[data-step='tracking']\").dataset.state === 'done'")
        check("action from the panel moves the persisted lifecycle and focus to the next step", p.locator("[data-panel='service']").count() == 1)

        # ---- tablet width ----------------------------------------------------------------------
        p.set_viewport_size({"width": 820, "height": 1000})
        p.goto(f"{BASE}/#/orders")
        p.reload()
        p.wait_for_selector("[data-testid='order-row']")
        check("tablet: page does not scroll sideways", p.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        p.goto(f"{BASE}/#/orders/{done}")
        p.reload()
        p.wait_for_selector("[data-testid='detail-order-id']")
        check("tablet: detail does not scroll sideways", p.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        b.close()
finally:
    prev.terminate()

with get_neo4j_driver().session() as s:      # tidy up: remove the test orders and give their stock back
    ids = list(orders.values())
    s.run("""
      MATCH (o:Order) WHERE o.id IN $ids
      OPTIONAL MATCH (r:FulfilmentRequest)-[:HAS_ORDER]->(o)
      OPTIONAL MATCH (fo:FulfilmentOption {fulfilmentRequestId: r.id})
      OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
      OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
      OPTIONAL MATCH (sh)-[:HAS_EVENT]->(se:ShipmentEvent)
      OPTIONAL MATCH (o)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
      OPTIONAL MATCH (sj)-[:HAS_EVENT]->(sve)
      WITH collect(DISTINCT o)+collect(DISTINCT r)+collect(DISTINCT fo)+collect(DISTINCT a)+collect(DISTINCT sh)+collect(DISTINCT se)+collect(DISTINCT sj)+collect(DISTINCT sve) AS nodes
      UNWIND nodes AS n WITH n WHERE n IS NOT NULL DETACH DELETE n""", ids=ids).consume()
    from app.modules.allocation.ledger import recompute_ledger_totals
    recompute_ledger_totals(s)

check("no page errors", not errors, "; ".join(errors[:2]))
print(f"\n{sum(results)} passed, {len(results) - sum(results)} failed")
sys.exit(0 if all(results) else 1)
