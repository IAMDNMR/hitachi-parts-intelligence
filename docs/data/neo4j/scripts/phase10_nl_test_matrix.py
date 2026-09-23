#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10 — Parts Intelligence natural-language test matrix (live).

Sends every question to POST /api/v1/intelligence/query (in-process TestClient,
live AuraDB, live Gemini when configured) and checks the result objectively:
the intent, and a fact that must hold in the graph evidence / data. Writes
docs/research/PHASE_10_NL_TEST_MATRIX.md.

    python docs/data/neo4j/scripts/phase10_nl_test_matrix.py
"""
import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "backend" / ".env")  # app settings read the environment at import

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

OUT = ROOT / "docs" / "research" / "PHASE_10_NL_TEST_MATRIX.md"
PACE_SECONDS = 9.0  # up to 2 Gemini calls per question -> <= ~13 calls/minute


def ev(r):
    return json.dumps(r["evidence"], default=str).lower()


def dealers(r):
    return [d["dealer_id"] for d in r["data"].get("dealers", [])]


def cards(r):
    return [c["part_id"] for c in r["data"].get("candidates", [])]


# (category, question, accepted intents, check(response) -> bool, must_mention_in_answer)
CASES = [
    ("part lookup", "What is PT-001?", {"part_info"}, lambda r: r["resolved_part_id"] == "PT-001", None),
    ("part lookup / everything", "Tell me everything about PT-045", {"part_info"},
     lambda r: r["evidence"]["suppliers"] and r["evidence"]["fits"]["machines"] == 7, "synthetic"),
    ("part category", "What category is PT-031?", {"part_info"}, lambda r: "genuine fluid" in ev(r), None),
    ("part → machine", "Which machines use PT-001?", {"impact_analysis"},
     lambda r: r["evidence"]["affected_machines"] == 4, None),
    ("impact", "Which machines could be affected if PT-045 is unavailable?", {"impact_analysis", "mitigation_analysis"},
     lambda r: "7" in ev(r), None),
    ("machine → part", "Which parts fit the ZX350?", {"machine_parts", "part_search"}, lambda r: len(cards(r)) > 0, None),
    ("part search + machine", "hydraulic filter for ZX210-7", {"part_search"}, lambda r: len(cards(r)) > 0, None),
    ("part search", "track roller", {"part_search"}, lambda r: cards(r)[:1] in (["PT-051"], ["PT-059"]), None),
    ("part number lookup", "4663907", {"part_search", "part_info"},
     lambda r: "PT-001" in cards(r) or r["resolved_part_id"] == "PT-001", None),
    ("alternatives", "Are there alternative parts for PT-045?", {"alternatives", "mitigation_analysis"},
     lambda r: "pt-044" in ev(r), None),
    ("part → depot", "Where does PT-045 come from?", {"supply_chain"}, lambda r: "oosterhout" in ev(r), "synthetic"),
    ("part → inventory", "Which depot supplies PT-001?", {"supply_chain"}, lambda r: "depot-oosterhout" in ev(r) or "oosterhout" in ev(r), None),
    ("fulfilment", "What fulfilment options are available for PT-001?", {"fulfilment_options", "supply_chain"},
     lambda r: "not_connected" in ev(r), None),
    ("source risk", "Is PT-045 single-source?", {"supplier_risk"},
     lambda r: r["evidence"]["single_point_of_failure"]["is_spof"] is True, "synthetic"),
    ("source risk", "What is the source risk for PT-001?", {"supplier_risk"},
     lambda r: r["evidence"]["dual_source"] is False, "synthetic"),
    ("compliance", "Does PT-031 have compliance requirements?", {"compliance_analysis"},
     lambda r: len(r["evidence"]["requirements"]) > 0, None),
    ("mitigation", "What mitigation options do we have for PT-045?", {"mitigation_analysis"},
     lambda r: r["data"].get("mitigation_options") is not None, None),
    ("NL dealer lookup", "Who are the Hitachi dealers in the Netherlands?", {"dealer_list"},
     lambda r: len(dealers(r)) == 19, None),
    ("country filter", "Show me all Hitachi dealers in Belgium", {"dealer_list"},
     lambda r: len(dealers(r)) == 4 and all(d.startswith("DLR-") for d in dealers(r)), None),
    ("city filter", "Which dealer is in Veldhoven?", {"dealer_list", "nearest_dealer"},
     lambda r: dealers(r)[:1] == ["DLR-122"], None),
    ("nearest dealer", "Which dealer is nearest to Amsterdam?", {"nearest_dealer"},
     lambda r: r["data"]["dealers"][0]["distance_km"] < 20
     and [d["distance_km"] for d in r["data"]["dealers"]] == sorted(d["distance_km"] for d in r["data"]["dealers"]), None),
    ("nearest dealer", "Who is the nearest Hitachi dealer to Eindhoven?", {"nearest_dealer"},
     lambda r: dealers(r)[:1] == ["DLR-122"], None),
    ("nearest dealer, no location", "Which is the nearest dealer to me in the Netherlands?", {"nearest_dealer"},
     lambda r: r["needs_clarification"] and "postcode" in r["answer"].lower(), None),
    ("nearest dealer by postcode", "Nearest dealer to postcode 5611 AB", {"nearest_dealer"},
     lambda r: dealers(r)[:1] == ["DLR-122"], None),
    ("dealer contact", "Give me the contact details for Pellen Machines", {"dealer_contact"},
     lambda r: "+31" in r["answer"] or "pellenbv" in r["answer"].lower(), None),
    ("part → dealer (multi-hop)", "Which dealers can support PT-045 in the Netherlands?", {"part_dealers"},
     lambda r: len(dealers(r)) > 0 and "derived" in ev(r), None),
    ("order, no id", "Where is my order?", {"order_status"},
     lambda r: r["needs_clarification"] and "order-demo-001" in r["answer"], None),
    ("order status", "What is the status of order-demo-001?", {"order_status"},
     lambda r: r["evidence"]["order"]["status"] == "ACCEPTED", "synthetic"),
    ("order → dealer", "Which dealer will receive order-demo-002?", {"order_status", "shipment_status"},
     lambda r: r["evidence"]["dealer"]["dealer_id"] == "DLR-001", None),
    ("order → service", "Has the part in order-demo-001 been installed?", {"service_status", "order_status"},
     lambda r: r["evidence"]["service_job"]["status"] == "COMPLETED", None),
    ("shipment", "Where is shipment ship-demo-002?", {"shipment_status"},
     lambda r: r["evidence"]["shipment"]["status"] == "SHIPPED", None),
    ("complete journey", "Give me the complete journey of order-demo-001", {"order_status"},
     lambda r: r["evidence"]["shipment"] and r["evidence"]["service_job"], "synthetic"),
    ("unsupported data", "What does PT-001 cost?", {"unsupported"}, lambda r: "not_connected" in ev(r), "not"),
    ("unknown part", "Tell me about PT-999", {"part_search", "part_info"},
     lambda r: not r["resolved_part_id"] and not cards(r), None),
    ("synthetic-data question", "How much stock of PT-045 is at the depot?", {"supply_chain", "unsupported"},
     lambda r: "synthetic" in ev(r) or "not_connected" in ev(r), "synthetic"),
]


def main():
    client = TestClient(app)
    rows, passed = [], 0
    for cat, q, intents, check, mention in CASES:
        time.sleep(PACE_SECONDS)  # stay under the Gemini free-tier 15 requests/minute
        t = time.perf_counter()
        r = client.post("/api/v1/intelligence/query", json={"query": q}).json()
        ms = round((time.perf_counter() - t) * 1000)
        try:
            ok_fact = bool(check(r))
        except Exception:
            ok_fact = False
        ok_intent = r.get("intent") in intents
        ok_mention = mention is None or mention in r.get("answer", "").lower()
        ok = ok_intent and ok_fact and ok_mention
        passed += ok
        rows.append((cat, q, r, ms, ok, ok_intent, ok_fact, ok_mention))
        print(f"{'PASS' if ok else 'FAIL'}  {ms:5}ms  [{r.get('intent')}] {q}")

    lines = [
        "# Phase 10 — Parts Intelligence Natural-Language Test Matrix",
        "",
        f"Run: {time.strftime('%Y-%m-%d %H:%M')} · live AuraDB · `POST /api/v1/intelligence/query` · "
        f"script `docs/data/neo4j/scripts/phase10_nl_test_matrix.py`",
        "",
        f"**Result: {passed}/{len(CASES)} PASS.** A case passes only if the intent is correct, the graph fact "
        "holds in the returned evidence/data, and (where listed) the answer states the provenance.",
        "",
        "| # | Category | Question | Intent | Entities | Graph path | Understand / Answer by | ms | Result |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, (cat, q, r, ms, ok, oi, of, om) in enumerate(rows, 1):
        ents = ", ".join(f"{k}={v}" for k, v in (r.get("entities") or {}).items() if v) or "—"
        why = "" if ok else " (" + ", ".join(n for n, v in (("intent", oi), ("fact", of), ("provenance", om)) if not v) + ")"
        p = r.get("pipeline", {})
        lines.append(f"| {i} | {cat} | {q} | {r.get('intent')} | {ents} | {' → '.join(r.get('graph_path', [])) or '—'} | "
                     f"{p.get('extraction')} / {p.get('answer')} | {ms} | {'PASS' if ok else 'FAIL' + why} |")
    lines += ["", "## Answers", ""]
    for i, (cat, q, r, *_rest) in enumerate(rows, 1):
        lines += [f"**{i}. {q}**", "", "> " + r.get("answer", "").replace("\n", "\n> "), ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{passed}/{len(CASES)} PASS -> {OUT}")


if __name__ == "__main__":
    main()
