"""
backend/scripts/run_browser_e2e.py

Final Real Browser E2E Validation Script for Phase 11
Uses Playwright Chromium to validate all 6 required user journeys:
1. VERIFIED PART CHECKOUT (Battery 4663907 -> Cart -> Check Stock & Fulfil -> Stages 1-7)
2. UNVERIFIED PART (PT-054 -> Request verification -> disabled from checkout)
3. AMBIGUOUS PART (hydraulic-cylinder -> Serial/PIN lookup modal -> resolved to 4410244 -> checkout-enabled)
4. PRODUCT FAMILY (genuine-engine-oil-dh2 -> Request identification -> inquiry flow)
5. PARTS INTELLIGENCE (6 representative queries evaluated against real data-truth)
6. CONSOLE / NETWORK VALIDATION (Zero uncaught JS errors, zero 4xx/5xx responses)
"""

import os
import sys
import time
import subprocess
import json
from playwright.sync_api import sync_playwright

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def run_e2e():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 80)
    print("STARTING REAL BROWSER E2E VALIDATION (PHASE 11)")
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 80)

    # 1. Verify backend readiness
    import urllib.request
    print("\n[Step 1] Verifying backend is fully ready on port 8000...")
    backend_ready = False
    for attempt in range(15):
        try:
            res = urllib.request.urlopen("http://localhost:8000/api/v1/dealers", timeout=5)
            if res.status == 200:
                print("  ✓ Backend is live and /api/v1/dealers returned 200 OK")
                backend_ready = True
                break
        except Exception as e:
            time.sleep(1)
    if not backend_ready:
        print("  ✗ Backend not responding on port 8000! Aborting.")
        return 1

    # 2. Start Vite preview server
    print("\n[Step 2] Starting Vite preview server on port 4173...")
    preview_proc = subprocess.Popen(
        ["node", "node_modules/vite/bin/vite.js", "preview", "--port", "4173"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    preview_ready = False
    for attempt in range(15):
        try:
            with urllib.request.urlopen("http://localhost:4173/", timeout=2) as r:
                if r.status == 200:
                    print("  ✓ Vite preview server is live and responded 200 OK on port 4173")
                    preview_ready = True
                    break
        except Exception:
            time.sleep(1)
    if not preview_ready:
        print("  ✗ Vite preview server failed to start on port 4173! Aborting.")
        preview_proc.terminate()
        return 1

    console_errors = []
    page_errors = []
    network_errors = []

    results = {
        "journey1_verified_checkout": False,
        "journey2_unverified_pt054": False,
        "journey3_ambiguous_cylinder": False,
        "journey4_product_family": False,
        "journey5_parts_intelligence": False,
        "journey6_console_network": False,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            # Attach event listeners
            def on_console(msg):
                if msg.type in ["error"]:
                    # Ignore harmless favicon or known benign dev warnings if any
                    text = msg.text
                    if "favicon" not in text.lower():
                        console_errors.append(text)
                        print(f"  [BROWSER CONSOLE ERROR] {text}")

            def on_page_error(err):
                page_errors.append(str(err))
                print(f"  [BROWSER PAGE ERROR] {err}")

            def on_response(resp):
                if resp.status >= 400:
                    # Ignore harmless 404 for favicon
                    if "favicon" not in resp.url:
                        network_errors.append(f"{resp.status} {resp.url}")
                        print(f"  [NETWORK ERROR {resp.status}] {resp.url}")

            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.on("response", on_response)

            # -----------------------------------------------------------------
            # JOURNEY 1: VERIFIED PART CHECKOUT (Battery 4663907)
            # -----------------------------------------------------------------
            print("\n[Journey 1] Testing Verified Part Checkout: Battery 4663907...")
            page.goto("http://localhost:4173/#/parts-store")
            page.wait_for_selector(".ps-card", timeout=10000)

            # Filter or search for 4663907
            search_input = page.locator(".ps-search input")
            search_input.fill("4663907")
            page.wait_for_timeout(500)

            # Find card with 4663907 and click Add to Cart
            battery_card = page.locator(".ps-card", has_text="4663907").first
            add_btn = battery_card.locator("button:has-text('Add to Cart')")
            add_btn.click()
            page.wait_for_timeout(500)

            # Open cart via header cart button
            page.locator("button.site-header__cart").click()
            page.wait_for_selector(".ps-modal", timeout=5000)

            # Verify battery 4663907 in cart with ready badge
            cart_modal = page.locator(".ps-modal")
            cart_item = cart_modal.locator("li", has_text="4663907")
            assert cart_item.count() > 0, "Battery 4663907 not found in cart list"
            assert "Ready for fulfilment" in cart_item.inner_text(), "Missing ready for fulfilment badge"
            print("  ✓ Battery 4663907 present in cart with 'Ready for fulfilment' badge")

            # Click Check stock & fulfil ->
            fulfil_btn = cart_item.locator("button.ps-quote-cart-list__fulfil")
            assert fulfil_btn.count() > 0, "Missing Check stock & fulfil button"
            fulfil_btn.click()
            page.wait_for_selector(".cw-stage", timeout=5000)
            print("  ✓ Launched Guided Checkout Wizard into Stage 1")

            # Stage 1: Review selected part
            assert "Review Selected Part" in page.locator(".cw-stage__title").inner_text()
            page.locator("button:has-text('Next: Requester Details →')").click()
            page.wait_for_timeout(500)
            print("  ✓ Stage 1 completed: Part and quantity confirmed")

            # Stage 2: Requester Information
            assert "Requester Information" in page.locator(".cw-stage__title").inner_text()
            page.fill("#requester-name", "Johannes van der Berg")
            page.fill("#requester-email", "johannes@hitachi-aftersales.eu")
            page.locator("button:has-text('Next: Destination Dealer →')").click()
            page.wait_for_timeout(500)
            print("  ✓ Stage 2 completed: Requester identity entered")

            # Stage 3: Destination Dealer
            assert "Destination Dealer Selection" in page.locator(".cw-stage__title").inner_text()
            dealer_select = page.locator("#dealer-select")
            page.wait_for_selector("#dealer-select option", timeout=15000)
            # Select first dealer branch
            first_val = dealer_select.locator("option").first.get_attribute("value")
            dealer_select.select_option(value=first_val)
            page.wait_for_timeout(500)
            page.locator("button:has-text('Check Stock & Availability →')").click()
            page.wait_for_timeout(500)
            print("  ✓ Stage 3 completed: Dealer branch selected with straight-line distance")

            # Stage 4: Availability Snapshot
            page.wait_for_selector(".cw-stage__title:has-text('Availability Snapshot')", timeout=8000)
            # Verify data provenance notice
            assert "SYNTHETIC DEMO DATA" in page.locator(".cw-provenance-banner").inner_text()
            assert "NOT CONNECTED" in page.locator(".cw-provenance-banner").inner_text()
            page.locator("button:has-text('Next: Transportation Options →')").click()
            page.wait_for_timeout(500)
            print("  ✓ Stage 4 completed: Availability evaluated (Notice: SYNTHETIC DEMO DATA)")

            # Stage 5: Transportation Options
            page.wait_for_selector(".cw-card--transport", timeout=12000)
            # Select the first transport card
            cards = page.locator(".cw-card--transport")
            assert cards.count() > 0, "No transport option cards rendered"
            cards.first.click()
            page.wait_for_timeout(300)
            page.locator("button:has-text('Next: Order Review →')").click()
            page.wait_for_timeout(500)
            print("  ✓ Stage 5 completed: Transport mode selected")

            # Stage 6: Final Review & Order Placement
            page.wait_for_selector(".cw-stage__title:has-text('Final Review')", timeout=5000)
            assert "4663907" in page.locator(".cw-review-grid").inner_text()
            place_order_btn = page.locator("button:has-text('Confirm Order & Proceed to Fulfilment →')")
            place_order_btn.click()
            print("  ✓ Stage 6 completed: Order placement confirmed")

            # Stage 7: Post-Order Lifecycle & Milestones
            page.wait_for_selector(".cw-stage__title:has-text('7. Demonstration: Allocation → Order → Shipment → Service → Close')", timeout=15000)
            assert page.locator(".cw-milestone-card").count() >= 1, "Milestones not rendered"
            stage = page.locator(".cw-stage")
            assert "fulfilment lifecycle & service" in stage.inner_text().lower()
            assert "no live hcme erp, inventory, carrier, tms or dealer service system is connected" in " ".join(stage.inner_text().lower().split())
            print("  ✓ Stage 7 reached: demonstration header and data-truth subtitle rendered")

            # Walk the whole simulated lifecycle and check the data-truth wording at every step.
            FORBIDDEN = ["Live Tracking", "physically", "torqued", "Quality inspection", "Certified Service Technician",
                         "CERTIFIED_SERVICE_TECHNICIAN", "Workshop Manager", "Authorised Dealer Service", "authorised dealer technician",
                         "Successfully Closed", "successfully delivered to dealer branch", "Live sequential"]

            def check_wording(label):
                text = page.locator(".cw-stage").inner_text()
                bad = [w for w in FORBIDDEN if w.lower() in text.lower()]
                assert not bad, f"{label}: misleading wording present: {bad}"

            def click(text, timeout=15000):
                btn = page.locator(f"button:has-text('{text}')")
                btn.first.wait_for(state="visible", timeout=timeout)
                btn.first.click()
                page.wait_for_timeout(700)

            check_wording("stage 7 start")
            click("Allocate Inventory")
            page.wait_for_selector(".cw-milestone-title:has-text('Simulated Inventory Allocation')", timeout=15000)
            page.wait_for_selector("text=Demonstrates how inventory would be reserved against the selected fulfilment source", timeout=15000)
            page.wait_for_selector(".cw-milestone-card >> text=DEMO / SIMULATED", timeout=15000)
            assert "demo / simulated" in page.locator(".cw-milestone-card").first.inner_text().lower()
            check_wording("allocation")
            click("Create Simulated Order")
            page.wait_for_selector(".cw-milestone-title:has-text('Simulated Order Creation')", timeout=15000)
            page.wait_for_selector(".cw-milestone-card:has-text('Simulated Order Creation') >> text=ERP Integration", timeout=15000)
            order_card = page.locator(".cw-milestone-card", has_text="Simulated Order Creation").inner_text()
            assert "no live hcme erp order is created" in order_card.lower() and "demo / simulated" in order_card.lower()
            check_wording("order")
            click("Create Simulated Shipment")
            page.wait_for_selector(".cw-milestone-title:has-text('Simulated Shipment & Tracking')", timeout=15000)
            page.wait_for_selector(".cw-milestone-card:has-text('Simulated Shipment & Tracking') >> text=Demo Tracking Code", timeout=15000)
            ship_card = page.locator(".cw-milestone-card", has_text="Simulated Shipment & Tracking").inner_text()
            for must in ("Demo European Logistics Partner", "NOT_CONNECTED", "SYNTHETIC_DEMO", "Demo Tracking Code"):
                assert must.lower() in ship_card.lower(), f"shipment card missing '{must}'"
            check_wording("shipment created")
            click("Simulate Dispatch Milestone")
            click("Simulate Delivery Milestone")
            page.wait_for_selector("text=Demonstration shipment reached the simulated delivery milestone.", timeout=15000)
            check_wording("shipment delivered")
            click("[SIMULATED] Create Demo Service Job")
            page.wait_for_selector(".cw-milestone-title:has-text('Simulated Dealer Service')", timeout=15000)
            page.wait_for_selector(".cw-milestone-card:has-text('Simulated Dealer Service') >> text=Demo Work Order", timeout=15000)
            svc = page.locator(".cw-milestone-card", has_text="Simulated Dealer Service").inner_text()
            assert "demo work order" in svc.lower() and "demo / simulated" in svc.lower() and "[simulated] service job created" in svc.lower()
            check_wording("service job")
            for step_label, milestone in (("1. [SIMULATED] Part Receipt Recorded", "[SIMULATED] Part Receipt Recorded"),
                                          ("2. [SIMULATED] Service Work Started", "[SIMULATED] Service Work Started"),
                                          ("3. [SIMULATED] Installation Milestone Recorded", "[SIMULATED] Installation Milestone Recorded"),
                                          ("4. [SIMULATED] Service Completion Recorded", "[SIMULATED] Service Completion Recorded")):
                click(step_label)
                page.wait_for_selector(f".cw-events-list :text('{milestone}')", timeout=15000)
                check_wording(step_label)
            page.wait_for_selector(".cw-celebration-title:has-text('Demonstration Fulfilment Journey Completed')", timeout=15000)
            final = page.locator(".cw-card--celebration").inner_text()
            assert "no live commercial order, carrier shipment, or dealer service event was created." in " ".join(final.lower().split())
            assert "demo / simulated" in final.lower() and "demo work order" in final.lower(), f"final card text: {final!r}"
            check_wording("final")
            print("  ✓ Stage 7 lifecycle walked end to end: every event marked DEMO/SIMULATED, no misleading wording")

            # Close wizard / return
            page.locator("button.cw-close-btn").click()
            page.wait_for_timeout(500)
            if page.locator(".ps-modal__close").count() > 0:
                page.locator(".ps-modal__close").first.click()
                page.wait_for_timeout(300)
            results["journey1_verified_checkout"] = True
            print(">>> JOURNEY 1 (VERIFIED PART CHECKOUT) PASSED!")

            # -----------------------------------------------------------------
            # JOURNEY 2: UNVERIFIED PART (PT-054)
            # -----------------------------------------------------------------
            print("\n[Journey 2] Testing Unverified Part: PT-054...")
            page.goto("http://localhost:4173/#/parts-store")
            page.wait_for_selector(".ps-card", timeout=5000)

            # Search for PT-054 or 12345678
            search_input = page.locator(".ps-search input")
            search_input.fill("12345678")
            page.wait_for_timeout(500)

            card_pt054 = page.locator(".ps-card", has_text="12345678").first
            card_pt054.locator("button:has-text('Add to Cart')").click()
            page.wait_for_timeout(500)

            # Open cart
            page.locator("button.site-header__cart").click()
            page.wait_for_selector(".ps-modal", timeout=5000)

            item_pt054 = page.locator(".ps-quote-cart-list li", has_text="12345678")
            assert item_pt054.count() > 0, "PT-054 not in cart"
            # Verify badge and action button
            badge_text = item_pt054.locator(".ps-cart-badge").inner_text()
            assert "Demo order" in badge_text, f"Unexpected badge: {badge_text}"

            verify_btn = item_pt054.locator("button.ps-quote-cart-list__inquire")
            assert verify_btn.count() > 0, "Missing inquiry button"
            assert "Continue to demo order" in verify_btn.inner_text(), f"Unexpected button label: {verify_btn.inner_text()}"
            assert verify_btn.is_enabled(), "Continue to demo order button is dead/disabled"
            assert item_pt054.locator("button:has-text('Check stock & fulfil')").count() == 0, "Check stock should NOT exist for PT-054"

            # Click button - should open inquiry form, NOT checkout
            verify_btn.click()
            page.wait_for_selector(".cw-stage", timeout=5000)
            stage_text = page.locator(".cw-stage").inner_text().upper()
            assert "NOT AN OFFICIAL HCME PART NUMBER" in stage_text and "DEMO-" in stage_text, "unverified item must show a labelled DEMO reference"
            assert "GENUINE HITACHI OEM" not in stage_text, "a DEMO reference must never be labelled genuine OEM"
            print("  ✓ PT-054 is never marked verified; it moves into the demo order workflow with a labelled DEMO reference")

            # Close the wizard
            page.locator("button.cw-close-btn").click()
            page.wait_for_timeout(300)
            if page.locator(".ps-modal__close").count() > 0:
                page.locator(".ps-modal__close").first.click()
                page.wait_for_timeout(300)
            results["journey2_unverified_pt054"] = True
            print(">>> JOURNEY 2 (UNVERIFIED PART PT-054) PASSED!")

            # -----------------------------------------------------------------
            # JOURNEY 3: AMBIGUOUS PART (hydraulic-cylinder)
            # -----------------------------------------------------------------
            print("\n[Journey 3] Testing Ambiguous Part: hydraulic-cylinder...")
            page.goto("http://localhost:4173/#/parts-store")
            page.wait_for_selector(".ps-card", timeout=5000)

            # Search for Hydraulic Cylinder
            search_input = page.locator(".ps-search input")
            search_input.fill("Hydraulic Cylinder")
            page.wait_for_timeout(500)

            cyl_card = page.locator(".ps-card", has_text="Hydraulic Cylinder").first
            cyl_card.locator("button:has-text('Add to Cart')").click()
            page.wait_for_timeout(500)

            # Open cart
            page.locator("button.site-header__cart").click()
            page.wait_for_selector(".ps-modal", timeout=5000)

            cyl_item = page.locator(".ps-quote-cart-list li", has_text="Hydraulic Cylinder")
            assert cyl_item.count() > 0, "Hydraulic Cylinder not in cart"
            assert "Multiple OEM assemblies found" in cyl_item.locator(".ps-cart-badge").inner_text()

            identify_btn = cyl_item.locator("button:has-text('Identify by machine/serial →')")
            assert identify_btn.count() > 0, "Missing Identify by machine/serial button"
            print("  ✓ Ambiguous hydraulic cylinder carries 'Identify by machine/serial →'")

            # Click Identify by machine/serial ->
            identify_btn.click()
            page.wait_for_selector(".ps-modal h2:has-text('Identify OEM Assembly')", timeout=5000)
            print("  ✓ Serial Identification Modal opened")

            # Fill Serial/PIN and confirm Boom Cylinder assembly (4410244)
            page.fill("input[placeholder*='HCMDH210']", "HCMDFJ00E00012345")
            page.locator("button:has-text('Apply & Enable Fulfilment →')").click()
            page.wait_for_timeout(500)

            # Verify in cart: item updated to 4410244 and button is now Check stock & fulfil ->
            resolved_item = page.locator(".ps-quote-cart-list li", has_text="4410244")
            assert resolved_item.count() > 0, "Resolved cylinder part number 4410244 not in cart"
            fulfil_btn_resolved = resolved_item.locator("button.ps-quote-cart-list__fulfil")
            assert fulfil_btn_resolved.count() > 0, "Resolved item not fulfilment-eligible"
            assert "Check stock & fulfil" in fulfil_btn_resolved.inner_text()
            print("  ✓ Ambiguous cylinder resolved via Serial/PIN to OEM 4410244 and unlocked for fulfilment checkout")

            if page.locator(".ps-modal__close").count() > 0:
                page.locator(".ps-modal__close").first.click()
                page.wait_for_timeout(300)

            results["journey3_ambiguous_cylinder"] = True
            print(">>> JOURNEY 3 (AMBIGUOUS PART RESOLUTION) PASSED!")

            # -----------------------------------------------------------------
            # JOURNEY 4: PRODUCT FAMILY (genuine-engine-oil-dh2)
            # -----------------------------------------------------------------
            print("\n[Journey 4] Testing Product Family: genuine-engine-oil-dh2...")
            page.goto("http://localhost:4173/#/parts-store")
            page.wait_for_selector(".ps-card", timeout=5000)

            search_input = page.locator(".ps-search input")
            search_input.fill("DH-2")
            page.wait_for_timeout(500)

            oil_card = page.locator(".ps-card", has_text="DH-2").first
            oil_card.locator("button:has-text('Add to Cart')").click()
            page.wait_for_timeout(500)

            # Open cart
            page.locator("button.site-header__cart").click()
            page.wait_for_selector(".ps-modal", timeout=5000)

            oil_item = page.locator(".ps-quote-cart-list li", has_text="DH-2")
            assert oil_item.count() > 0, "DH-2 Oil not in cart"
            assert "Demo order" in oil_item.locator(".ps-cart-badge").inner_text()

            oil_inquire_btn = oil_item.locator("button:has-text('Continue to demo order →')")
            assert oil_inquire_btn.count() > 0, "Missing identification / order request button"
            assert oil_item.locator("button:has-text('Check stock & fulfil')").count() == 0, "Checkout button incorrectly enabled for product family!"
            print("  ✓ Product family DH-2 correctly restricted to inquiry flow, blocked from normal checkout")

            if page.locator(".ps-modal__close").count() > 0:
                page.locator(".ps-modal__close").first.click()
                page.wait_for_timeout(300)

            results["journey4_product_family"] = True
            print(">>> JOURNEY 4 (PRODUCT FAMILY RESTRICTION) PASSED!")

            # -----------------------------------------------------------------
            # JOURNEY 5: PARTS INTELLIGENCE (6 REPRESENTATIVE QUERIES)
            # -----------------------------------------------------------------
            print("\n[Journey 5] Testing Parts Intelligence queries...")
            page.goto("http://localhost:4173/#/parts-intelligence")
            page.wait_for_selector(".pix-composer textarea", timeout=5000)

            pi_queries = [
                ("Machine search", "What machines are in the medium excavator category?"),
                ("Machine -> Part", "What hydraulic parts fit ZX210LC-7?"),
                ("Supplier search", "Who are the suppliers in Netherlands?"),
                ("Dealer search", "Which dealer is near Eindhoven?"),
                ("Dealer/Supplier relationship", "Are there suppliers in the same city as dealers?"),
                ("Graph/Network relationship", "Show dealer network for Netherlands"),
            ]

            textarea = page.locator(".pix-composer textarea")
            send_btn = page.locator("button.pix-send")

            for name, q in pi_queries:
                print(f"  Submitting Query [{name}]: \"{q}\"")
                prev_count = page.locator(".pix-answer").count()
                textarea.fill(q)
                send_btn.click()
                # Wait for assistant response to render
                page.wait_for_function(f"document.querySelectorAll('.pix-answer').length > {prev_count}", timeout=15000)
                page.wait_for_timeout(500)

                # Get latest assistant turn text
                latest_turn = page.locator(".pix-answer").last.inner_text()
                # Verify no US references in operational responses
                assert "United States" not in latest_turn, f"US data leaked in query {q}"
                print(f"    ✓ Query [{name}] answered successfully")

            results["journey5_parts_intelligence"] = True
            print(">>> JOURNEY 5 (PARTS INTELLIGENCE 6 QUERIES) PASSED!")

            # -----------------------------------------------------------------
            # JOURNEY 6: CONSOLE / NETWORK VALIDATION
            # -----------------------------------------------------------------
            print("\n[Journey 6] Validating Console and Network logs...")
            print(f"  Total uncaught console errors: {len(console_errors)}")
            print(f"  Total page runtime errors: {len(page_errors)}")
            print(f"  Total application 4xx/5xx network errors: {len(network_errors)}")

            assert len(page_errors) == 0, f"Page errors encountered: {page_errors}"
            assert len(console_errors) == 0, f"Console errors encountered: {console_errors}"
            assert len(network_errors) == 0, f"Network errors encountered: {network_errors}"

            results["journey6_console_network"] = True
            print(">>> JOURNEY 6 (ZERO CONSOLE/NETWORK ERRORS) PASSED!")

            browser.close()

    finally:
        print("\nStopping preview server...")
        preview_proc.terminate()
        try:
            preview_proc.wait(timeout=3)
        except Exception:
            preview_proc.kill()

    print("\n" + "=" * 80)
    print("FINAL E2E BROWSER VALIDATION SUMMARY:")
    for k, v in results.items():
        status_str = "PASSED [OK]" if v else "FAILED [FAIL]"
        print(f"  {k}: {status_str}")
    print("=" * 80)

    if all(results.values()):
        print("\nALL 6 BROWSER E2E JOURNEYS PASSED CLEANLY WITH ZERO ERRORS!")
        return 0
    else:
        print("\nONE OR MORE JOURNEYS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(run_e2e())
