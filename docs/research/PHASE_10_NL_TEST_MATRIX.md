# Phase 10 — Parts Intelligence Natural-Language Test Matrix

Run: 2026-09-23 15:58 · live AuraDB · `POST /api/v1/intelligence/query` · script `docs/data/neo4j/scripts/phase10_nl_test_matrix.py`

**Result: 32/35 PASS.** A case passes only if the intent is correct, the graph fact holds in the returned evidence/data, and (where listed) the answer states the provenance.

| # | Category | Question | Intent | Entities | Graph path | Understand / Answer by | ms | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | part lookup | What is PT-001? | part_info | part_ref=PT-001 | Part → Machine → Assembly → Supplier → ComplianceRequirement → Alternative Part → InventorySnapshot → Order | deterministic / deterministic | 7010 | PASS |
| 2 | part lookup / everything | Tell me everything about PT-045 | part_info | part_ref=PT-045 | Part → Machine → Assembly → Supplier → ComplianceRequirement → Alternative Part → InventorySnapshot → Order | deterministic / deterministic | 6239 | PASS |
| 3 | part category | What category is PT-031? | part_info | part_ref=PT-031 | Part → Machine → Assembly → Supplier → ComplianceRequirement → Alternative Part → InventorySnapshot → Order | deterministic / deterministic | 2896 | PASS |
| 4 | part → machine | Which machines use PT-001? | impact_analysis | part_ref=PT-001 | Part → Assembly (BOM) → Machine | deterministic / deterministic | 6072 | PASS |
| 5 | impact | Which machines could be affected if PT-045 is unavailable? | impact_analysis | part_ref=PT-045 | Part → Assembly (BOM) → Machine | deterministic / gemini | 4562 | PASS |
| 6 | machine → part | Which parts fit the ZX350? | machine_parts | machine_ref=ZX350 | Part → Machine (fitment filter) | deterministic / deterministic | 4633 | PASS |
| 7 | part search + machine | hydraulic filter for ZX210-7 | part_search | machine_ref=ZX210-7 | Part → Machine (fitment filter) | deterministic / deterministic | 478 | PASS |
| 8 | part search | track roller | part_search | — | Part | deterministic / deterministic | 324 | PASS |
| 9 | part number lookup | 4663907 | part_search | part_ref=4663907 | Part | deterministic / deterministic | 490 | PASS |
| 10 | alternatives | Are there alternative parts for PT-045? | alternatives | part_ref=PT-045 | Part → Machine → Alternative Part | deterministic / deterministic | 5809 | PASS |
| 11 | part → depot | Where does PT-045 come from? | supply_chain | part_ref=PT-045 | Part → Supplier → InventorySnapshot → Depot | deterministic / deterministic | 2570 | PASS |
| 12 | part → inventory | Which depot supplies PT-001? | supplier_risk | part_ref=PT-001 | Part → Supplier → Assembly (criticality) | deterministic / deterministic | 5843 | FAIL (intent, fact) |
| 13 | fulfilment | What fulfilment options are available for PT-001? | fulfilment_options | part_ref=PT-001 | Part → Supplier → InventorySnapshot → Depot → FulfilmentOption | deterministic / deterministic | 5365 | PASS |
| 14 | source risk | Is PT-045 single-source? | supplier_risk | part_ref=PT-045 | Part → Supplier → Assembly (criticality) | deterministic / deterministic | 2452 | PASS |
| 15 | source risk | What is the source risk for PT-001? | supplier_risk | part_ref=PT-001 | Part → Supplier → Assembly (criticality) | deterministic / deterministic | 6018 | PASS |
| 16 | compliance | Does PT-031 have compliance requirements? | compliance_analysis | part_ref=PT-031 | Part → Assembly → ComplianceRequirement | deterministic / deterministic | 5892 | PASS |
| 17 | mitigation | What mitigation options do we have for PT-045? | mitigation_analysis | part_ref=PT-045 | Part → Machine → Alternative Part → Supplier → ComplianceRequirement | deterministic / deterministic | 1870 | PASS |
| 18 | NL dealer lookup | Who are the Hitachi dealers in the Netherlands? | dealer_list | country=NL | DealerBranch | deterministic / deterministic | 5236 | PASS |
| 19 | country filter | Show me all Hitachi dealers in Belgium | dealer_list | country=BE | DealerBranch | deterministic / deterministic | 5146 | PASS |
| 20 | city filter | Which dealer is in Veldhoven? | dealer_list | place=Veldhoven | DealerBranch | deterministic / deterministic | 1159 | PASS |
| 21 | nearest dealer | Which dealer is nearest to Amsterdam? | nearest_dealer | place=Amsterdam | Location → DealerBranch (distance) | deterministic / gemini | 14850 | PASS |
| 22 | nearest dealer | Who is the nearest Hitachi dealer to Eindhoven? | nearest_dealer | place=Eindhoven | — | deterministic / clarification | 11637 | FAIL (fact) |
| 23 | nearest dealer, no location | Which is the nearest dealer to me in the Netherlands? | nearest_dealer | country=NL | — | deterministic / clarification | 14 | PASS |
| 24 | nearest dealer by postcode | Nearest dealer to postcode 5611 AB | nearest_dealer | place=5611 AB | — | deterministic / clarification | 10223 | FAIL (fact) |
| 25 | dealer contact | Give me the contact details for Pellen Machines | dealer_contact | dealer_name=Pellen Machines | DealerBranch | deterministic / deterministic | 6701 | PASS |
| 26 | part → dealer (multi-hop) | Which dealers can support PT-045 in the Netherlands? | part_dealers | part_ref=PT-045, country=NL | Part → Machine → Machine category → DealerBranch (product categories) | deterministic / deterministic | 6168 | PASS |
| 27 | order, no id | Where is my order? | order_status | — | — | deterministic / clarification | 213 | PASS |
| 28 | order status | What is the status of order-demo-001? | order_status | order_ref=order-demo-001 | Order → Part → Allocation → Shipment → ShipmentEvent → DealerBranch → ServiceJob | deterministic / deterministic | 5782 | PASS |
| 29 | order → dealer | Which dealer will receive order-demo-002? | order_status | order_ref=order-demo-002 | Order → Part → Allocation → Shipment → ShipmentEvent → DealerBranch → ServiceJob | deterministic / deterministic | 1754 | PASS |
| 30 | order → service | Has the part in order-demo-001 been installed? | service_status | order_ref=order-demo-001 | Order → Part → Allocation → Shipment → ShipmentEvent → DealerBranch → ServiceJob | deterministic / deterministic | 1345 | PASS |
| 31 | shipment | Where is shipment ship-demo-002? | shipment_status | shipment_ref=ship-demo-002 | Order → Part → Allocation → Shipment → ShipmentEvent → DealerBranch → ServiceJob | deterministic / deterministic | 5232 | PASS |
| 32 | complete journey | Give me the complete journey of order-demo-001 | order_status | order_ref=order-demo-001 | Order → Part → Allocation → Shipment → ShipmentEvent → DealerBranch → ServiceJob | deterministic / deterministic | 5215 | PASS |
| 33 | unsupported data | What does PT-001 cost? | unsupported | part_ref=PT-001 | — | deterministic / deterministic | 1741 | PASS |
| 34 | unknown part | Tell me about PT-999 | part_search | part_ref=PT-999 | Part | deterministic / deterministic | 768 | PASS |
| 35 | synthetic-data question | How much stock of PT-045 is at the depot? | supply_chain | part_ref=PT-045 | Part → Supplier → InventorySnapshot → Depot | deterministic / gemini | 3748 | PASS |

## Answers

**1. What is PT-001?**

> PT-001 is Battery - Starter, Lighting & Ignition (Electrical / Battery), fitted to 4 machine model(s) according to HCME Europe source data. Supplier(s): Demo Battery Supplier; compliance gaps: 0; 5 candidate alternative(s). Suppliers, stock, certificates and orders are based on synthetic demo data; live HCME ERP data is not connected.

**2. Tell me everything about PT-045**

> PT-045 is Hitachi OEM Dual Axial Piston Main Hydraulic Pump (Hydraulics / Hydraulic Pump), fitted to 7 machine model(s) according to HCME Europe source data. Supplier(s): Demo Hydraulics Supplier A; compliance gaps: 0; 1 candidate alternative(s). Suppliers, stock, certificates and orders are based on synthetic demo data; live HCME ERP data is not connected.

**3. What category is PT-031?**

> PT-031 is Hitachi Genuine Hydraulic Oil 5000 (Genuine Fluid / Hydraulic oil), fitted to 67 machine model(s) according to HCME Europe source data. Supplier(s): Demo Lubricants Supplier; compliance gaps: 0; 3 candidate alternative(s). Suppliers, stock, certificates and orders are based on synthetic demo data; live HCME ERP data is not connected.

**4. Which machines use PT-001?**

> PT-001 is fitted to 4 machine model(s) (HCME Europe source fitment data).

**5. Which machines could be affected if PT-045 is unavailable?**

> The Hitachi OEM Dual Axial Piston Main Hydraulic Pump (PT-045) is applicable to the following seven machine models:
> 
> - ZX210LC-7 / ZX210LCN-7 (Excavators)
> - ZX225USR-7 (Excavators)
> - ZX250LC-7 / ZX250LCN-7 (Excavators)
> - ZX300LC-7 / ZX300LCN-7 (Excavators)
> - ZX350-7G (Excavators)
> - ZX350LC-7 / ZX350LCN-7 (Excavators)
> - ZX375US-7 (Excavators)
> 
> Based on the HCME Europe published dataset, the part is used in the upperstructure main hydraulic pump assembly. The BOM quantities and assembly criticality are based on synthetic demo data.

**6. Which parts fit the ZX350?**

> Found 10 matching part(s) in the HCME Europe catalogue. Best match: PT-026 Hitachi Genuine Oil Filter (90%).

**7. hydraulic filter for ZX210-7**

> Found 4 matching part(s) in the HCME Europe catalogue. Best match: PT-026 Hitachi Genuine Oil Filter (90%).

**8. track roller**

> Found 3 matching part(s) in the HCME Europe catalogue. Best match: PT-051 Hitachi OEM Forged Dual-Flange Lower Track Roller Assembly (100%).

**9. 4663907**

> Found 1 matching part(s) in the HCME Europe catalogue. Best match: PT-001 Battery - Starter, Lighting & Ignition (100%).

**10. Are there alternative parts for PT-045?**

> Closest alternative to PT-045: PT-044 (80% similar). Treat as a candidate for review, not an approved replacement.

**11. Where does PT-045 come from?**

> PT-045 is supplied (synthetic demo data) and stocked at the Hitachi European Parts Centre, Oosterhout (demo stock).

**12. Which depot supplies PT-001?**

> PT-001 is single-sourced. Sole-sourced, but not used in any high-criticality assembly. This is based on synthetic demo supplier data.

**13. What fulfilment options are available for PT-001?**

> PT-001 is supplied (synthetic demo data) and stocked at the Hitachi European Parts Centre, Oosterhout (demo stock).

**14. Is PT-045 single-source?**

> PT-045 is single-sourced. Sole-sourced from Demo Hydraulics Supplier A and used in high-criticality assemblies (Main Hydraulic Pump). This is based on synthetic demo supplier data.

**15. What is the source risk for PT-001?**

> PT-001 is single-sourced. Sole-sourced, but not used in any high-criticality assembly. This is based on synthetic demo supplier data.

**16. Does PT-031 have compliance requirements?**

> PT-031 has 3 compliance requirement(s) and 0 gap(s). Assembly-level assignments and certificates are synthetic demo data.

**17. What mitigation options do we have for PT-045?**

> If PT-045 (Hitachi OEM Dual Axial Piston Main Hydraulic Pump) becomes unavailable, 7 machine model(s) are affected on high-criticality paths. It is sole-sourced from Demo Hydraulics Supplier A. 1 alternative(s) found; best is PT-044 (similarity 80%, mitigation score 84, no compliance gaps).

**18. Who are the Hitachi dealers in the Netherlands?**

> The HCME Europe dealer dataset lists 19 dealer location(s) for NL.

**19. Show me all Hitachi dealers in Belgium**

> The HCME Europe dealer dataset lists 4 dealer location(s) for BE.

**20. Which dealer is in Veldhoven?**

> The HCME Europe dealer dataset lists 1 dealer location(s) for Veldhoven.

**21. Which dealer is nearest to Amsterdam?**

> Based on the HCME Europe dealer locator (SRC-049) dataset, the nearest dealer to Amsterdam is Hitachi Construction Machinery (Europe) N.V. located in Amsterdam at Sicilieweg 5, 1045 AT Amsterdam, at a straight-line distance of 0.0 km.

**22. Who is the nearest Hitachi dealer to Eindhoven?**

> I could not locate 'Eindhoven'. Please give another city or a postcode.

**23. Which is the nearest dealer to me in the Netherlands?**

> Which city or postcode in NL should I use to find the nearest Hitachi dealer?

**24. Nearest dealer to postcode 5611 AB**

> I could not locate '5611 AB'. Please give another city or a postcode.

**25. Give me the contact details for Pellen Machines**

> Pellen Machines Veldhoven BV (Veldhoven, NL): phone +31 (0)40-25-32-470, email info@pellenbv.nl.

**26. Which dealers can support PT-045 in the Netherlands?**

> No verified dealer-to-part relationship exists; 15 dealer(s) in NL handle the machine categories (Excavators) this part fits.

**27. Where is my order?**

> Which order do you mean? Live HCME ERP/order data is not currently connected, so I can only look up orders in the demo dataset: order-12d0d7d4-7ce6-4e6e-813e-7f1ff3ded9cd, order-282645c0-e508-400f-99ff-fab413cb8629, order-29870e4e-ca33-4f41-a0e1-7a523643eb82, order-3177d758-1336-4dae-bd1a-1b4d56be4094, order-362635ed-fa74-464c-b78a-a07cbcec747b, order-3da3b25e-4af9-406b-aea8-1e51c5c1ee65, order-4850398a-8f4e-4422-83cc-d3abf0042505, order-4db45fcb-575a-4ead-ab81-3aa2e77d1a2a, order-5726d594-c5d5-4eaa-9913-131b096ada61, order-8a36f148-5fc2-45f4-9402-0b763821cb72, order-a6ed2f74-3010-43e0-b345-045eae2912c6, order-a815f314-bb71-44ad-8431-12478c5d47cc, order-bb2b04b7-3798-49f5-a992-ad7748bed580, order-bd9fbd4e-a971-4bcd-a081-be4b508f2a36, order-ca0e97e7-2ed1-4be9-acdc-971bee568d3f, order-cabcf2a9-1f58-4d5e-aed8-91a71d34723a, order-demo-001, order-demo-002, order-demo-003, order-fdd145bc-3b93-4169-889a-137d559f689d, order-ffd3020b-6ae1-4d25-af6f-7f206a9a370a.

**28. What is the status of order-demo-001?**

> Order order-demo-001 is ACCEPTED for 2 × Battery - Starter, Lighting & Ignition. Shipment: DELIVERED. Receiving dealer: Danny Bergmans. This is based on synthetic demo operational data.

**29. Which dealer will receive order-demo-002?**

> Order order-demo-002 is ACCEPTED for 1 × Battery - Starter, Lighting & Ignition. Shipment: SHIPPED. Receiving dealer: AC Plant Sales. This is based on synthetic demo operational data.

**30. Has the part in order-demo-001 been installed?**

> Order order-demo-001 is ACCEPTED for 2 × Battery - Starter, Lighting & Ignition. Shipment: DELIVERED. Receiving dealer: Danny Bergmans. This is based on synthetic demo operational data.

**31. Where is shipment ship-demo-002?**

> Order order-demo-002 is ACCEPTED for 1 × Battery - Starter, Lighting & Ignition. Shipment: SHIPPED. Receiving dealer: AC Plant Sales. This is based on synthetic demo operational data.

**32. Give me the complete journey of order-demo-001**

> Order order-demo-001 is ACCEPTED for 2 × Battery - Starter, Lighting & Ignition. Shipment: DELIVERED. Receiving dealer: Danny Bergmans. This is based on synthetic demo operational data.

**33. What does PT-001 cost?**

> That information is not available: live HCME pricing, lead-time and ERP data are not currently connected.

**34. Tell me about PT-999**

> No part in the current HCME Europe catalogue matches that description.

**35. How much stock of PT-045 is at the depot?**

> Based on the HCME Europe published facility facts, the Hitachi European Parts Centre is located in Oosterhout, Netherlands, but the current HCME Europe dataset does not contain per-part stock figures. Note: this is based on synthetic demo data (no live HCME stock feed is connected), which indicates a quantity of 40 units at the Hitachi European Parts Centre, Oosterhout.
