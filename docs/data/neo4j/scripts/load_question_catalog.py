#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10E — load the Parts Intelligence question catalogue into Aura and wire
it to the real graph.

    python docs/data/neo4j/scripts/load_question_catalog.py            # dry run
    python docs/data/neo4j/scripts/load_question_catalog.py --execute

Source of truth for questions: docs/data/parts_intelligence/
HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv. Source of truth for intents:
INTENT_SPEC in backend/app/modules/intelligence/intent_resolution.py.

Nodes (data_source='HCME_PI_QUESTION_CATALOG', INTERNAL_REFERENCE_ONLY — this
is routing metadata, never presented as HCME operational data):
  (:QuestionCategory)<-[:IN_CATEGORY]-(:QuestionTemplate)-[:HAS_INTENT]->(:Intent)
  (:Intent)-[:TRAVERSES {step}]->(:RelationshipType)          live counts/provenance
Derived taxonomy (DERIVED from existing Machine/Part properties):
  (:Machine)-[:OF_TYPE]->(:MachineType)     from Machine.machine_subcategory
  (:Part)-[:OF_TYPE]->(:PartType)           from Part.part_subcategory
Template -> real-node wiring (only where the template names the entity):
  ABOUT_PART, ABOUT_MACHINE, ABOUT_MACHINE_TYPE, ABOUT_PART_TYPE, ABOUT_DEALER,
  ABOUT_SUPPLIER, ABOUT_DEPOT, ABOUT_CITY, FILTERS_COUNTRY
Nothing here creates a Supplier->Part, Supplier->Dealer or Supplier->Depot edge.
"""
import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / "backend" / ".env")

from app.modules.intelligence.graph_query import MACHINE_TYPE_VOCAB, PART_CATEGORY_VOCAB  # noqa: E402
from app.modules.intelligence.intent_resolution import INTENT_SPEC  # noqa: E402

CSV = ROOT / "docs" / "data" / "parts_intelligence" / "HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv"
SRC = "HCME_PI_QUESTION_CATALOG"

REL_CLASS = {  # relationship type -> (classification, note)
    "HAS_PART_FITMENT": ("SOURCE_DERIVED", "HCME Europe fitment data"),
    "SUPPLIED_BY": ("SYNTHETIC_DEMO", "demo suppliers only; the SAP supplier master has no part numbers"),
    "LOCATED_IN": ("SOURCE_DERIVED", "supplier master / dealer locator city"),
}
# CSV `intent` cells carry notes ("part_search (fallback - ...)"); the routed intent is the first token.
def clean_intent(raw: str) -> str:
    return raw.split(" (")[0].strip()


def read_rows():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in rows:
        r["intent_clean"] = clean_intent(r["intent"])
        r["enabled"] = r["enabled"].strip().upper() == "TRUE" and r.get("verified", "TRUE").strip().upper() == "TRUE"
        r["follow_up_required"] = r["follow_up_required"].strip().upper() == "TRUE"
    return rows


def wiring(session, r):
    """Real-node links for one template, derived from the entities it names."""
    text = r["question_template"]
    low = text.lower()
    links = []
    if r["part_entity"]:
        links.append(("ABOUT_PART", "Part", "part_id", r["part_entity"].upper()))
    if r["machine_entity"]:
        me = r["machine_entity"].strip()
        if me.lower() in MACHINE_TYPE_VOCAB:
            links.append(("ABOUT_MACHINE_TYPE", "MachineType", "name", MACHINE_TYPE_VOCAB[me.lower()]))
        else:
            row = session.run("MATCH (m:Machine) WHERE m.model = $m RETURN m.machine_id AS id", m=me).single()
            if row:
                links.append(("ABOUT_MACHINE", "Machine", "machine_id", row["id"]))
    if r["country_filter"]:
        links.append(("FILTERS_COUNTRY", "Country", "code", r["country_filter"].strip().upper()))
    for key in sorted(PART_CATEGORY_VOCAB, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", low):
            links.append(("ABOUT_PART_TYPE", "PartType", "name", PART_CATEGORY_VOCAB[key]))
            break
    m = re.search(r"supplier (\d{6,10})", low)
    if m:
        links.append(("ABOUT_SUPPLIER", "Supplier", "supplier_number", m.group(1).zfill(10)))
    if "depot" in low:
        links.append(("ABOUT_DEPOT", "Depot", "depot_id", "DEPOT-OOSTERHOUT"))
    d = session.run(
        "MATCH (d:DealerBranch) WHERE $q CONTAINS toLower(d.dealer_name) OR "
        "toLower(d.dealer_name) STARTS WITH toLower($first) RETURN d.dealer_id AS id",
        q=low, first=" ".join(re.findall(r"[A-Za-z]+", text)[-2:]) if "Pellen" in text else "~~none~~").single()
    if "pellen machines" in low and d:
        links.append(("ABOUT_DEALER", "DealerBranch", "dealer_id", d["id"]))
    for city in re.findall(r"\b(?:in|to|as)\s+(?:the\s+)?([A-Z][a-z]+)\b", text):
        if city not in ("Netherlands", "Germany", "Pellen"):
            c = session.run("MATCH (c:City) WHERE toLower(c.name)=toLower($n) RETURN c.city_id AS id "
                            "ORDER BY c.country = 'NL' DESC LIMIT 1", n=city).single()
            if c:
                links.append(("ABOUT_CITY", "City", "city_id", c["id"]))
    return links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    rows = read_rows()
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    with driver.session(database=os.environ.get("NEO4J_DATABASE") or None) as s:
        plan = {r["question_id"]: wiring(s, r) for r in rows}
        unknown = sorted({r["intent_clean"] for r in rows} - set(INTENT_SPEC))
        print(f"templates: {len(rows)} | categories: {len({r['category'] for r in rows})} | "
              f"intents in use: {len({r['intent_clean'] for r in rows})} | intents missing from INTENT_SPEC: {unknown}")
        for qid, links in plan.items():
            print(f"  {qid}: " + ", ".join(f"{t}->{lbl}({v})" for t, lbl, _k, v in links))
        if not args.execute:
            print("DRY RUN — re-run with --execute.")
            return

        for stmt in (
            "CREATE CONSTRAINT question_template_id IF NOT EXISTS FOR (q:QuestionTemplate) REQUIRE q.question_id IS UNIQUE",
            "CREATE CONSTRAINT intent_name IF NOT EXISTS FOR (i:Intent) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT question_category_name IF NOT EXISTS FOR (c:QuestionCategory) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT relationship_type_name IF NOT EXISTS FOR (r:RelationshipType) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT machine_type_name IF NOT EXISTS FOR (t:MachineType) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT part_type_name IF NOT EXISTS FOR (t:PartType) REQUIRE t.name IS UNIQUE",
        ):
            s.run(stmt).consume()

        # Derived taxonomy on existing real nodes.
        n1 = s.run("""MATCH (m:Machine) WHERE m.machine_subcategory IS NOT NULL
                      MERGE (t:MachineType {name: m.machine_subcategory})
                        ON CREATE SET t.data_source='DERIVED', t.derived_from='Machine.machine_subcategory'
                      MERGE (m)-[r:OF_TYPE]->(t) SET r.data_source='DERIVED'
                      RETURN count(r) AS n""").single()["n"]
        n2 = s.run("""MATCH (p:Part) WHERE p.part_subcategory IS NOT NULL
                      MERGE (t:PartType {name: p.part_subcategory})
                        ON CREATE SET t.data_source='DERIVED', t.derived_from='Part.part_subcategory'
                      MERGE (p)-[r:OF_TYPE]->(t) SET r.data_source='DERIVED'
                      RETURN count(r) AS n""").single()["n"]

        # Relationship types with LIVE counts and honest provenance.
        rel_names = sorted({x for spec in INTENT_SPEC.values() if spec[3] for x in spec[3].split(">")})
        for rn in rel_names:
            cls, note = REL_CLASS.get(rn, ("UNKNOWN", ""))
            cnt = s.run(f"MATCH ()-[r:{rn}]->() RETURN count(r) AS n").single()["n"]
            real = s.run(f"MATCH ()-[r:{rn}]->() WHERE coalesce(r.synthetic,false)=false RETURN count(r) AS n").single()["n"]
            s.run("""MERGE (r:RelationshipType {name:$n})
                     SET r.classification=$c, r.note=$note, r.total_edges=$cnt, r.real_edges=$real,
                         r.data_source=$src, r.data_class='INTERNAL_REFERENCE_ONLY', r.refreshed_at=datetime()""",
                  n=rn, c=cls, note=note, cnt=cnt, real=real, src=SRC).consume()

        # Intents (from the routing code's own spec) and their traversal steps.
        for name, (rtype, src_e, req_e, rel) in INTENT_SPEC.items():
            s.run("""MERGE (i:Intent {name:$name})
                     SET i.result_type=$rt, i.source_entity=$se, i.requested_entity=$re,
                         i.relationship_required=$rel, i.data_source=$src, i.data_class='INTERNAL_REFERENCE_ONLY'""",
                  name=name, rt=rtype, se=src_e, re=req_e, rel=rel, src=SRC).consume()
            for step, rn in enumerate((rel or "").split(">") if rel else []):
                s.run("""MATCH (i:Intent {name:$name}), (r:RelationshipType {name:$rn})
                         MERGE (i)-[t:TRAVERSES]->(r) SET t.step=$step""", name=name, rn=rn, step=step).consume()

        # Templates + wiring.
        for r in rows:
            s.run("""MERGE (c:QuestionCategory {name:$cat})
                     SET c.data_source=$src, c.data_class='INTERNAL_REFERENCE_ONLY'
                     MERGE (q:QuestionTemplate {question_id:$id})
                     SET q.question_template=$text, q.intent=$intent, q.result_type=$rt, q.enabled=$en,
                         q.follow_up_required=$fu, q.follow_up_type=$fut, q.fallback=$fb,
                         q.relationship_path=$rp, q.data_requirement=$dr, q.catalog_data_class=$dc, q.verified=$vf, q.verified_on=$vo,
                         q.data_source=$src, q.data_class='INTERNAL_REFERENCE_ONLY', q.refreshed_at=datetime()
                     MERGE (q)-[:IN_CATEGORY]->(c)
                     WITH q
                     OPTIONAL MATCH (i:Intent {name:$intent})
                     FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END | MERGE (q)-[:HAS_INTENT]->(i))""",
                  cat=r["category"], id=r["question_id"], text=r["question_template"], intent=r["intent_clean"],
                  rt=r["result_type"], en=r["enabled"], fu=r["follow_up_required"], fut=r["follow_up_type"] or None,
                  fb=r["fallback"] or None, rp=r["relationship_path"] or None, dr=r["data_requirement"] or None,
                  dc=r["data_class"], vf=r.get("verified", "").upper() == "TRUE", vo=r.get("verified_on") or None, src=SRC).consume()
            s.run("MATCH (q:QuestionTemplate {question_id:$id})-[x]->(n) WHERE type(x) STARTS WITH 'ABOUT_' OR type(x)='FILTERS_COUNTRY' DELETE x",
                  id=r["question_id"]).consume()
            for rel, label, key, val in plan[r["question_id"]]:
                s.run(f"MATCH (q:QuestionTemplate {{question_id:$id}}), (n:{label} {{{key}:$v}}) MERGE (q)-[:{rel}]->(n)",
                      id=r["question_id"], v=val).consume()
        print(f"APPLIED  OF_TYPE edges: {n1} Machine->MachineType, {n2} Part->PartType; "
              f"{len(rows)} templates, {len(INTENT_SPEC)} intents, {len(rel_names)} relationship types")
    driver.close()


if __name__ == "__main__":
    main()
