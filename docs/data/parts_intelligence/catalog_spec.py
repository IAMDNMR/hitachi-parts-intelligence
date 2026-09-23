"""
Parts Intelligence question catalogue — the single spec.

Each question is paired with the CHECK that proves its answer is right. A
question only reaches the UI catalogue (enabled=TRUE in the CSV and in Aura)
after verify_question_catalog.py has run it through the production pipeline
and the check passed, under BOTH the no-LLM provider and a Gemini-outage
provider. Checks assert facts that hold in the live graph, never wording.

Columns mirror HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv.
"""


def _n(r, key):
    return len(r["data"].get(key) or [])


def _cards(r):
    return [c["part_id"] for c in r["data"].get("candidates") or []]


def _has(r, *words):
    a = r["answer"].lower()
    return all(w.lower() in a for w in words)


# id, category, question, intent, result_type, part, machine, country, relationship_path, data_requirement, check
Q = [
    # ---------------------------------------------------------------- Parts Search
    ("P01", "Parts Search", "Which parts fit my medium excavator?", "machine_parts_by_category", "PART_RESULTS",
     "", "medium excavator", "", "Machine -[:HAS_PART_FITMENT]-> Part", "SOURCE_DERIVED",
     lambda r: r["entities"]["machine_type"] == "Medium Excavators" and _n(r, "parts") > 0 and _n(r, "machine_options") > 0),
    ("P02", "Parts Search", "What hydraulic parts fit ZX210LC-7?", "machine_parts", "PART_RESULTS",
     "", "ZX210LC-7", "", "Machine -[:HAS_PART_FITMENT]-> Part", "SOURCE_DERIVED",
     lambda r: _cards(r) and all("hydraulic" in (c["part_name"] + " " + str(c["category"]) + " " + str(c["subcategory"]) + " " + str(c["assembly"])).lower()
                                  for c in r["data"]["candidates"])),
    ("P03", "Parts Search", "Find battery parts", "part_search", "PART_RESULTS",
     "", "", "", "Part", "SOURCE_DERIVED",
     lambda r: _cards(r) and all("battery" in (c["part_name"] + str(c["subcategory"])).lower() for c in r["data"]["candidates"])),
    ("P04", "Parts Search", "Show track roller parts", "part_search", "PART_RESULTS",
     "", "", "", "Part", "SOURCE_DERIVED",
     lambda r: _cards(r) and all("roller" in (c["part_name"] + str(c["subcategory"])).lower() for c in r["data"]["candidates"][:2])),
    ("P05", "Parts Search", "Tell me everything about PT-001.", "part_info", "PART_RESULTS",
     "PT-001", "", "", "Part (+ fitment, assemblies, compliance, alternatives)", "SOURCE_DERIVED",
     lambda r: r["resolved_part_id"] == "PT-001" and r["insights_part_id"] == "PT-001" and _has(r, "PT-001")),
    ("P06", "Parts Search", "Are there alternatives for PT-007?", "alternatives", "PART_RESULTS",
     "PT-007", "", "", "Part -> (same part type, shared fitment) Part - candidates for engineering review", "DERIVED",
     lambda r: r["resolved_part_id"] == "PT-007" and _has(r, "engineering review") and _has(r, "PT-015") and _has(r, "not an approved replacement")),
    ("P07", "Parts Search", "Are there alternatives for PT-045?", "alternatives", "INSUFFICIENT_DATA",
     "PT-045", "", "", "Part -> (same part type, shared fitment) Part - none exist", "DERIVED",
     lambda r: r["resolved_part_id"] == "PT-045" and _has(r, "no candidate") and r["result_type"] in ("INSUFFICIENT_DATA", "NO_RELATIONSHIP")),
    # ---------------------------------------------------------------- Dealers
    ("D01", "Dealers", "Which dealers are in Netherlands?", "dealer_list", "DEALER_RESULTS",
     "", "", "NL", "DealerBranch -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "SOURCE_DERIVED",
     lambda r: _n(r, "dealers") == 19 and all(d["country"] == "NL" for d in r["data"]["dealers"])),
    ("D02", "Dealers", "Which dealers are in Germany?", "dealer_list", "DEALER_RESULTS",
     "", "", "DE", "DealerBranch -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "SOURCE_DERIVED",
     lambda r: _n(r, "dealers") == 68 and all(d["country"] == "DE" for d in r["data"]["dealers"])),
    ("D03", "Dealers", "Which dealer is closest to Eindhoven?", "nearest_dealer", "DEALER_RESULTS",
     "", "", "", "City coordinates -> DealerBranch (distance)", "DERIVED",
     lambda r: r["data"]["dealers"][0]["dealer_id"] == "DLR-122" and r["data"]["dealers"][0]["distance_km"] < 10),
    ("D04", "Dealers", "Show me Pellen Machines.", "dealer_lookup", "DEALER_RESULTS",
     "", "", "", "DealerBranch", "SOURCE_DERIVED",
     lambda r: r["data"]["dealers"][0]["dealer_id"] == "DLR-122" and r["graph"] is not None and not r["data"].get("machines")),
    ("D05", "Dealers", "Which dealers are in Veldhoven?", "dealer_list", "DEALER_RESULTS",
     "", "", "", "DealerBranch -[:LOCATED_IN]-> City", "SOURCE_DERIVED",
     lambda r: any(d["dealer_id"] == "DLR-122" for d in r["data"]["dealers"])),
    # ---------------------------------------------------------------- Relationships
    ("R01", "Relationships", "Show me the dealers and suppliers in Netherlands.", "dealer_supplier_network", "NETWORK_RESULTS",
     "", "", "NL", "DealerBranch/Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "DERIVED",
     lambda r: r["graph"] and len(r["graph"]["nodes"]) > 2 and "SAME CITY" in r["graph"]["relationship_note"].upper()),
    ("R02", "Relationships", "Which suppliers are in the same city as Pellen Machines?", "supplier_lookup", "NETWORK_RESULTS",
     "", "", "", "DealerBranch -[:LOCATED_IN]-> City <-[:LOCATED_IN]- Supplier", "DERIVED",
     lambda r: _n(r, "suppliers") == 2 and "Veldhoven" in r["answer"] and r["graph"] is not None),
    ("R03", "Relationships", "Which suppliers are in the same city as the Oosterhout depot?", "supplier_lookup", "NETWORK_RESULTS",
     "", "", "", "Depot -[:LOCATED_IN]-> City <-[:LOCATED_IN]- Supplier", "DERIVED",
     lambda r: _n(r, "suppliers") > 0 and "Oosterhout" in r["answer"] and "depot" in r["answer"].lower()),
    ("R04", "Relationships", "Which cities have both dealers and suppliers?", "dealer_supplier_network", "NETWORK_RESULTS",
     "", "", "", "DealerBranch -[:LOCATED_IN]-> City <-[:LOCATED_IN]- Supplier", "DERIVED",
     lambda r: _n(r, "cities_with_both") > 3 and r["graph"] is not None),
    ("R07", "Relationships", "Show me the Netherlands dealer and supplier network.", "dealer_supplier_network", "NETWORK_RESULTS",
     "", "", "NL", "DealerBranch/Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "DERIVED",
     lambda r: r["graph"] is not None and "NL" in r["answer"] and _n(r, "shared_cities") > 0),
    ("R05", "Relationships", "Show me the supply chain for PT-001.", "supply_chain", "GRAPH_PATH",
     "PT-001", "", "", "Part -> InventorySnapshot -> Depot (demo) / Part -> Supplier (demo)", "SYNTHETIC_DEMO",
     lambda r: r["graph"] is not None and _has(r, "synthetic") and r["resolved_part_id"] == "PT-001"),
    ("R06", "Relationships", "Where is PT-001 available?", "supply_chain", "GRAPH_PATH",
     "PT-001", "", "", "Part -> InventorySnapshot -> Depot (demo)", "SYNTHETIC_DEMO",
     lambda r: r["intent"] == "supply_chain" and _has(r, "oosterhout") and _has(r, "synthetic")),
    # ---------------------------------------------------------------- Suppliers
    ("S01", "Suppliers", "Which suppliers are in Germany?", "supplier_lookup", "SUPPLIER_RESULTS",
     "", "", "DE", "Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "SOURCE_DERIVED",
     lambda r: "117" in r["answer"] and _n(r, "suppliers") > 0 and r["insights_part_id"] is None and not _cards(r)),
    ("S02", "Suppliers", "Which suppliers are in Netherlands?", "supplier_lookup", "SUPPLIER_RESULTS",
     "", "", "NL", "Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "SOURCE_DERIVED",
     lambda r: "1131" in r["answer"] and _n(r, "suppliers") > 0),
    ("S03", "Suppliers", "Which suppliers are in Oosterhout?", "supplier_lookup", "SUPPLIER_RESULTS",
     "", "", "", "Supplier -[:LOCATED_IN]-> City", "SOURCE_DERIVED",
     lambda r: "34" in r["answer"] and _n(r, "suppliers") > 0),
    ("S07", "Suppliers", "Which suppliers are in Eindhoven?", "supplier_lookup", "SUPPLIER_RESULTS",
     "", "", "", "Supplier -[:LOCATED_IN]-> City", "SOURCE_DERIVED",
     lambda r: _n(r, "suppliers") > 0 and "Eindhoven" in r["answer"]),
    ("S04", "Suppliers", "Show me supplier 0000100026.", "supplier_lookup", "SUPPLIER_RESULTS",
     "", "", "", "Supplier", "SOURCE_DERIVED",
     lambda r: _n(r, "suppliers") == 1 and r["data"]["suppliers"][0]["supplier_number"] == "0000100026"),
    ("S05", "Suppliers", "Which countries have suppliers?", "supplier_summary", "SUPPLIER_RESULTS",
     "", "", "", "Supplier -[:LOCATED_IN]-> City -[:IN_COUNTRY]-> Country", "SOURCE_DERIVED",
     lambda r: "1720" in r["answer"] and _n(r, "country_counts") > 20),
    ("S06", "Suppliers", "Which suppliers provide buckets for my medium excavator?", "machine_supplier_by_part_category", "NO_RELATIONSHIP",
     "", "medium excavator", "", "Machine -> Part -> [:SUPPLIED_BY] -> Supplier (not recorded)", "NOT_CONNECTED",
     lambda r: r["result_type"] in ("NO_RELATIONSHIP", "INSUFFICIENT_DATA") and _has(r, "not recorded") and not r["data"].get("suppliers")),
    # ---------------------------------------------------------------- Machines & Fleet
    ("M01", "Machines & Fleet", "What machines do we have?", "machine_list", "MACHINE_RESULTS",
     "", "", "", "Machine (all categories)", "SOURCE_DERIVED",
     lambda r: "77" in r["answer"] and r["graph"] is not None),
    ("M02", "Machines & Fleet", "Show me the medium excavators.", "machine_list", "MACHINE_RESULTS",
     "", "medium excavator", "", "Machine -[:OF_TYPE]-> MachineType", "SOURCE_DERIVED",
     lambda r: _n(r, "machines") == 16),
    ("M03", "Machines & Fleet", "Which machines use PT-001?", "impact_analysis", "MACHINE_RESULTS",
     "PT-001", "", "", "Part <- HAS_PART_FITMENT - Machine", "SOURCE_DERIVED",
     lambda r: _n(r, "machines") == 4 and r["graph"] is not None and "77" not in r["answer"]),
    ("M04", "Machines & Fleet", "Tell me about ZX210LC-7.", "machine_info", "MACHINE_RESULTS",
     "", "ZX210LC-7", "", "Machine -[:HAS_PART_FITMENT]-> Part", "SOURCE_DERIVED",
     lambda r: r["data"]["machines"][0]["model"] == "ZX210LC-7" and _has(r, "ZX210LC-7") and _cards(r)),
    ("M05", "Machines & Fleet", "Are there multi-grade oil alternatives for genuine engine oil?", "alternatives", "INSUFFICIENT_DATA",
     "", "", "", "Part (product domain)", "SOURCE_DERIVED",
     lambda r: r["result_type"] == "INSUFFICIENT_DATA" and r["resolved_part_id"] is None and "PT-001" not in r["answer"]),
    # ---------------------------------------------------------------- Orders & Service
    ("O01", "Orders & Service", "What is the status of order-demo-001?", "order_status", "ORDER_JOURNEY",
     "", "", "", "Order -> Shipment -> DealerBranch -> ServiceJob", "SYNTHETIC_DEMO",
     lambda r: r["evidence"]["order"]["status"] == "ACCEPTED" and _has(r, "synthetic")),
    ("O02", "Orders & Service", "Which dealer receives order-demo-002?", "order_status", "ORDER_JOURNEY",
     "", "", "", "Order -> Shipment -> DealerBranch", "SYNTHETIC_DEMO",
     lambda r: r["evidence"]["dealer"]["dealer_id"] == "DLR-001"),
    ("O03", "Orders & Service", "Show me the complete journey of order-demo-001.", "order_status", "ORDER_JOURNEY",
     "", "", "", "Order -> Allocation -> Shipment -> DealerBranch -> ServiceJob", "SYNTHETIC_DEMO",
     lambda r: bool(r["evidence"]["shipment"]) and r["evidence"]["service_job"]["status"] == "COMPLETED"),
]
