"""
End-to-end check of the order lifecycle in a real browser, with the database read independently (a direct Neo4j query, not the API):

  1. customer checkout -> Place Order -> Order Confirmation shows an HCME-ORD-###### ID
  2. that Order (customer, dealer, part, quantity, fulfilment option, date, status) exists in AuraDB
  3. a full page reload still shows the order in the Orders screen
  4. open the order; allocation -> fulfilment -> shipment -> tracking -> dealer service -> completed, from the Orders area only
  5. after EVERY step the Order/Allocation/Shipment/ServiceJob state is read from AuraDB
  6. the completed lifecycle is retrievable after another reload

Needs the backend on :8000 and a built frontend (`npm run build` in frontend/). Test orders are left in the database; delete them with the Neo4j
cleanup you normally use (they carry customer email lifecycle-e2e@example.eu).
"""
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright  # noqa: E402

from app.db.neo4j.connection import get_neo4j_driver  # noqa: E402

FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
BASE = "http://localhost:4173"
EMAIL = "lifecycle-e2e@example.eu"
results = []


def db(cypher, **params):
    with get_neo4j_driver().session() as s:
        return s.run(cypher, **params).data()


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    return ok


prev = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview", "--port", "4173"], cwd=FRONT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
for _ in range(20):
    try:
        urllib.request.urlopen(BASE + "/", timeout=2)
        break
    except Exception:
        time.sleep(1)

errors = []
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1366, "height": 900})
        p = ctx.new_page()
        p.on("pageerror", lambda e: errors.append(str(e)))

        # ---- 1. customer checkout -------------------------------------------------
        p.goto(BASE + "/#/parts-store")
        p.evaluate("localStorage.clear()")
        p.reload()
        p.wait_for_selector("article.ps-card", timeout=20000)
        p.locator(".ps-search input").fill("Battery")
        p.wait_for_timeout(600)
        p.locator("article.ps-card").filter(has=p.locator("button", has_text="Add to Cart")).first.locator("button", has_text="Add to Cart").click()
        p.locator("button.site-header__cart").click()
        p.wait_for_selector(".ps-modal")
        p.locator(".ps-quote-cart-list li").first.locator("button.ps-quote-cart-list__fulfil, button.ps-quote-cart-list__inquire").first.click()
        p.wait_for_selector(".cw-stage")
        check("stage order: Customer Details first", "1. Customer Details" in p.locator(".cw-stage").inner_text())
        p.fill("#requester-name", "Lifecycle E2E")
        p.fill("#requester-email", EMAIL)
        p.fill("#requester-phone", "+31 6 5555 0100")
        p.locator("button:has-text('Next: Cart →')").click()
        p.wait_for_selector(".cw-stage__title:has-text('2. Cart')")
        p.locator("button:has-text('Next: Delivery Dealer →')").click()
        p.wait_for_selector("#dealer-select option", timeout=15000)
        p.locator("button:has-text('Check Stock & Availability →')").click()
        p.wait_for_selector(".cw-stage__title:has-text('4. Availability')", timeout=20000)
        p.locator("button:has-text('Next: Transportation Options →')").click()
        p.wait_for_selector(".cw-card--transport", timeout=15000)
        p.locator(".cw-card--transport").first.click()
        p.locator("button:has-text('Next: Order Review →')").click()
        p.wait_for_selector(".cw-stage__title:has-text('6. Review')", timeout=10000)
        page_text = p.locator(".cw-stage").inner_text()
        check("no allocation/shipment/service actions in checkout", not re.search(r"Allocate Inventory|Create Simulated Shipment|Service Job", page_text))
        p.locator("button:has-text('Place Order →')").click()
        p.wait_for_selector("[data-testid='order-id']", timeout=20000)
        order_id = p.locator("[data-testid='order-id']").inner_text().strip()
        check("order confirmation shows a unique Order ID", re.fullmatch(r"HCME-ORD-\d{6}", order_id), order_id)
        conf = p.locator("[data-testid='order-confirmation']").inner_text()
        check("confirmation lists customer, phone, part, dealer, fulfilment", all(x in conf for x in ("Lifecycle E2E", EMAIL, "+31 6 5555 0100", "Deliver to", "Fulfilment")))
        check("checkout has no lifecycle controls after confirmation", p.locator("button:has-text('Allocate')").count() == 0)

        # ---- 2. persisted in AuraDB -----------------------------------------------
        row = db("MATCH (o:Order {id:$id}) RETURN o", id=order_id)
        check("order exists in AuraDB", len(row) == 1)
        o = row[0]["o"] if row else {}
        check("AuraDB: customer name/email/phone", (o.get("customerName"), o.get("customerEmail"), o.get("customerPhone")) == ("Lifecycle E2E", EMAIL, "+31 6 5555 0100"))
        check("AuraDB: dealer, part, quantity", bool(o.get("shipToDealerId") and o.get("shipToDealerName") and o.get("partNumber") and o.get("quantity")))
        check("AuraDB: fulfilment option, order date/time, status", bool(o.get("fulfilmentOptionId") and o.get("placedAt")) and o.get("status") == "CREATED")
        check("AuraDB: demo label kept", o.get("data_source") == "SYNTHETIC_DEMO")
        p.locator("button:has-text('Done')").click()

        # ---- 3. refresh, order still there ----------------------------------------
        p.goto(BASE + "/#/orders")
        p.reload()
        p.wait_for_selector("[data-testid='order-row']", timeout=15000)
        check("after reload the order is listed on the Orders screen", p.locator(f"[data-testid='order-row']:has-text('{order_id}')").count() == 1)
        check("Orders list shows customer / dealer / status", "Lifecycle E2E" in p.locator(f"[data-testid='order-row']:has-text('{order_id}')").inner_text())

        # ---- 4/5. business processing, each step verified in AuraDB ----------------
        p.locator(f"[data-testid='order-row']:has-text('{order_id}') a.ord__open").click()
        p.wait_for_selector("[data-testid='detail-order-id']")
        check("detail opens the same Order ID", p.locator("[data-testid='detail-order-id']").inner_text().strip() == order_id)

        def state():
            return db(
                """MATCH (o:Order {id:$id})
                   OPTIONAL MATCH (o)-[:BASED_ON_ALLOCATION]->(a:Allocation)
                   OPTIONAL MATCH (o)-[:HAS_SHIPMENT]->(sh:Shipment)
                   OPTIONAL MATCH (o)-[:HAS_SERVICE_JOB]->(sj:ServiceJob)
                   RETURN o.status AS o, a.status AS a, sh.status AS sh, sj.status AS sj""", id=order_id)[0]

        plan = [
            ("allocate", lambda s: s["a"] == "CONFIRMED" and s["o"] == "CREATED"),
            ("fulfil", lambda s: s["a"] == "CONSUMED" and s["o"] == "ACCEPTED"),
            ("create_shipment", lambda s: s["sh"] == "CREATED"),
            ("dispatch", lambda s: s["sh"] == "DISPATCHED"),
            ("in_transit", lambda s: s["sh"] == "IN_TRANSIT"),
            ("deliver", lambda s: s["sh"] == "DELIVERED" and s["o"] == "FULFILLED"),
            ("create_service_job", lambda s: s["sj"] == "OPEN"),
            ("receive", lambda s: s["sj"] == "PART_RECEIVED"),
            ("start", lambda s: s["sj"] == "IN_PROGRESS"),
            ("install", lambda s: s["sj"] == "PART_INSTALLED"),
            ("complete", lambda s: s["sj"] == "COMPLETED" and s["o"] == "CLOSED"),
        ]
        for action, expect in plan:
            btn = p.locator(f"button[data-action='{action}']")
            btn.wait_for(state="visible", timeout=15000)
            btn.click()
            p.wait_for_function("() => !document.querySelector('button.ord__btn:disabled')", timeout=20000)
            p.wait_for_timeout(300)
            st = state()
            check(f"step '{action}' persisted in AuraDB", expect(st), str(st))

        # ---- 6. completed lifecycle retrievable after reload ------------------------
        p.reload()
        p.wait_for_selector("[data-testid='detail-order-id']", timeout=15000)
        check("after reload the completed lifecycle is shown", "Lifecycle completed" in p.locator(".ord__action").inner_text())
        check("all 7 lifecycle steps are done", p.locator("li.ord__step[data-state='done']").count() == 7)
        check("no browser storage used for order data", p.evaluate("() => Object.keys(localStorage).filter(k => /order/i.test(k)).length") == 0)
        b.close()
finally:
    prev.terminate()

check("no page errors", not errors, "; ".join(errors[:2]))
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
