#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify every catalogue question against the production pipeline and publish
only the ones that pass.

    python docs/data/neo4j/scripts/verify_question_catalog.py            # report only
    python docs/data/neo4j/scripts/verify_question_catalog.py --publish  # + rewrite CSV enabled flags

Each question runs through POST /api/v1/intelligence/query (real route ->
route_and_answer_query -> live Neo4j) under two providers: no LLM, and a
Gemini client whose every call fails. A question is verified only if its
check passes under BOTH and its intent + result_type match the spec.
"""
import argparse
import csv
import io
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "docs" / "data" / "parts_intelligence"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "backend" / ".env")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.intelligence import assistant  # noqa: E402
from app.modules.intelligence.providers import DeterministicLLMProvider, GeminiLLMProvider, GeminiProviderError  # noqa: E402
from catalog_spec import Q  # noqa: E402

CSV = ROOT / "docs" / "data" / "parts_intelligence" / "HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv"
COLUMNS = ["question_id", "category", "question_template", "intent", "requested_entity", "machine_entity", "part_entity",
           "part_category", "dealer_entity", "supplier_entity", "depot_entity", "country_filter", "city_filter",
           "relationship_path", "required_graph_relationships", "follow_up_required", "follow_up_type", "result_type",
           "relationship_display", "data_requirement", "fallback", "data_class", "enabled", "verified", "verified_on"]


class GeminiDown(GeminiLLMProvider):
    def __init__(self):
        super().__init__(api_key="x", model="down")

    def _generate(self, *a, **k):
        raise GeminiProviderError("simulated outage")


def run(question, provider_factory):
    assistant.get_llm_provider = provider_factory
    r = TestClient(app).post("/api/v1/intelligence/query", json={"query": question, "context_part_id": "PT-001"})
    assert r.status_code == 200, r.text
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    results = []
    for qid, cat, text, intent, rtype, part, machine, country, path, dreq, check in Q:
        problems = []
        for name, factory in (("no-LLM", DeterministicLLMProvider), ("gemini-down", GeminiDown)):
            try:
                r = run(text, lambda f=factory: f())
                if r["intent"] != intent:
                    problems.append(f"{name}: intent {r['intent']} != {intent}")
                if r["result_type"] != rtype:
                    problems.append(f"{name}: result_type {r['result_type']} != {rtype}")
                if not check(r):
                    problems.append(f"{name}: check failed — answer: {r['answer'][:110]!r}")
            except Exception as e:  # a crashing check is a failing question, never a skipped one
                problems.append(f"{name}: {type(e).__name__}: {e}"[:160])
        results.append((qid, text, not problems, problems))
        print(f"{'PASS' if not problems else 'FAIL'}  {qid}  {text}")
        for p in problems:
            print(f"        - {p}")

    passed = sum(1 for r in results if r[2])
    print(f"\n{passed}/{len(results)} questions verified")

    if args.publish:
        ok = {r[0]: r[2] for r in results}
        rows = []
        for qid, cat, text, intent, rtype, part, machine, country, path, dreq, _ in Q:
            rows.append({
                "question_id": qid, "category": cat, "question_template": text, "intent": intent,
                "requested_entity": "", "machine_entity": machine, "part_entity": part, "part_category": "",
                "dealer_entity": "", "supplier_entity": "", "depot_entity": "", "country_filter": country,
                "city_filter": "", "relationship_path": path, "required_graph_relationships": "",
                "follow_up_required": "FALSE", "follow_up_type": "", "result_type": rtype, "relationship_display": "",
                "data_requirement": dreq, "fallback": "", "data_class": dreq,
                "enabled": "TRUE" if ok[qid] else "FALSE", "verified": "TRUE" if ok[qid] else "FALSE",
                "verified_on": str(date.today()) if ok[qid] else "",
            })
        with open(CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        print(f"CSV rewritten: {CSV.name} ({sum(ok.values())} enabled)")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
