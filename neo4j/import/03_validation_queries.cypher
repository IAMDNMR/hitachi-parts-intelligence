// =============================================================================
// Validation queries — for execution AFTER a real Aura import, not now.
// Expected counts are documented in neo4j/IMPORT_DESIGN_REPORT.md §11 and
// were dry-run validated against the CSVs directly (§12 of the same report).
// =============================================================================

// 1. Count Machines (expect 77)
MATCH (m:Machine) RETURN count(m) AS machine_count;

// 2. Count Parts (expect 43: 20 ORDERABLE_OEM_PART + 23 PRODUCT_LINE_PART_FAMILY)
MATCH (p:Part) RETURN p.record_class AS record_class, count(p) AS n ORDER BY record_class;

// 3. Count Services (expect 22)
MATCH (s:Service) RETURN count(s) AS service_count;

// 4. Count Attachments (expect 17)
MATCH (a:Attachment) RETURN count(a) AS attachment_count;

// 5. Count Digital Services (expect 8 distinct nodes, 616 HAS_DIGITAL_SERVICE relationships)
MATCH (d:DigitalService) RETURN count(d) AS digital_service_count;
MATCH ()-[r:HAS_DIGITAL_SERVICE]->() RETURN count(r) AS has_digital_service_count;

// 6. Find parts for a machine, with evidence
MATCH (m:Machine {machine_id: $machineId})-[f:HAS_PART_FITMENT]->(p:Part)
RETURN p.part_id, p.part_name, p.record_class, f.evidence, f.confidence
ORDER BY f.evidence;

// 7. Show fitment evidence distribution (expect CATEGORY 876, EXACT_MODEL 37, MODEL_RANGE 31)
MATCH ()-[f:HAS_PART_FITMENT]->() RETURN f.evidence AS evidence, count(f) AS n ORDER BY n DESC;

// 8. Find services for a machine, with applicability
MATCH (m:Machine {machine_id: $machineId})-[hs:HAS_SERVICE]->(s:Service)
RETURN s.service_name, hs.applicability, hs.confidence;

// 9. Find parts associated with a service
MATCH (s:Service {service_id: $serviceId})-[r:REQUIRES_PART]->(p:Part)
RETURN p.part_id, p.part_name, r.quantity, r.mandatory_optional;

// 10. Find attachments for a machine (model-level FITS only — see IMPORT_DESIGN_REPORT.md §13
// for why category-level attachment compatibility isn't a graph edge in this phase)
MATCH (m:Machine {machine_id: $machineId})<-[f:FITS]-(a:Attachment)
RETURN a.attachment_id, a.attachment_name, f.evidence;

// 11. Show a machine's after-sales ecosystem
MATCH (m:Machine {machine_id: $machineId})
OPTIONAL MATCH (m)-[:HAS_PART_FITMENT]->(p:Part)
OPTIONAL MATCH (m)-[:HAS_SERVICE]->(s:Service)
OPTIONAL MATCH (m)-[:HAS_DIGITAL_SERVICE]->(d:DigitalService)
OPTIONAL MATCH (m)-[:HAS_APPLICATION]->(app:Application)
OPTIONAL MATCH (m)<-[:FITS]-(a:Attachment)
RETURN m, collect(DISTINCT p) AS parts, collect(DISTINCT s) AS services,
       collect(DISTINCT d) AS digitalServices, collect(DISTINCT app) AS applications,
       collect(DISTINCT a) AS attachments;

// 12. Find derived relationships (any relationship type carrying relationship_class = 'DERIVED')
MATCH ()-[r]->() WHERE r.relationship_class = 'DERIVED' RETURN type(r) AS relationship_type, count(r) AS n ORDER BY n DESC;

// 13. Find relationships without provenance (should return 0 rows — every
// imported relationship type sets source_id or data_class in this design)
MATCH ()-[r]->()
WHERE r.source_id IS NULL AND r.data_class IS NULL
RETURN type(r) AS relationship_type, count(r) AS n;

// 14. Find duplicate business identifiers (should return 0 rows for every label —
// this is the live-database equivalent of the dry-run duplicate-ID check)
MATCH (n) WHERE n.machine_id IS NOT NULL
WITH n.machine_id AS id, count(n) AS n WHERE n > 1 RETURN 'Machine' AS label, id, n
UNION
MATCH (n) WHERE n.part_id IS NOT NULL
WITH n.part_id AS id, count(n) AS n WHERE n > 1 RETURN 'Part' AS label, id, n
UNION
MATCH (n) WHERE n.category_id IS NOT NULL
WITH n.category_id AS id, count(n) AS n WHERE n > 1 RETURN 'Category' AS label, id, n
UNION
MATCH (n) WHERE n.service_id IS NOT NULL
WITH n.service_id AS id, count(n) AS n WHERE n > 1 RETURN 'Service' AS label, id, n
UNION
MATCH (n) WHERE n.attachment_id IS NOT NULL
WITH n.attachment_id AS id, count(n) AS n WHERE n > 1 RETURN 'Attachment' AS label, id, n;

// 15. Find orphan nodes (no relationships at all — every Category/Machine/Part/
// Service/Attachment/DigitalService/Channel should have at least one edge
// after a full import; Specification and Application always attach via
// HAS_SPECIFICATION/HAS_APPLICATION so an orphan there means a broken MATCH
// during relationship load, worth investigating, not expected)
MATCH (n)
WHERE (n:Category OR n:Machine OR n:Part OR n:Service OR n:Attachment OR n:DigitalService OR n:Channel OR n:Specification OR n:Application)
  AND NOT (n)--()
RETURN labels(n) AS label, count(n) AS orphan_count;
