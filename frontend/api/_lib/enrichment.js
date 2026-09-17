import { withSession } from './neo4j.js'

/**
 * Same vocabulary translation as the rest of this project's Neo4j work:
 * Aura's HAS_PART_FITMENT.evidence values versus the level strings
 * pages/PartsStore/compatibility.js already understands. A translation of
 * spelling, not a reinterpretation of the underlying fact.
 */
const EVIDENCE_TO_LEVEL = {
  EXACT_MODEL: 'EXACT MODEL',
  MODEL_RANGE: 'MODEL/RANGE',
  CATEGORY: 'CATEGORY',
}

/**
 * Enrichment data for the EXISTING Parts Store catalogue, keyed by the one
 * identifier both sides share reliably: Part Number. This never returns a
 * new catalogue, a replacement image, or a replacement name — only
 * additional, verified relationships (today: compatible machines) for a
 * part the site already lists.
 *
 * A part number with no fitment rows in the graph is left out of the map
 * entirely — there is nothing to add, which the caller treats identically
 * to "no match found". Nothing here invents a compatibility fact: every
 * entry traces to a real HAS_PART_FITMENT relationship.
 */
export async function getEnrichmentByPartNumber() {
  const result = await withSession((session) =>
    session.run(`
      MATCH (p:Part)
      WHERE p.part_number IS NOT NULL
      OPTIONAL MATCH (m:Machine)-[r:HAS_PART_FITMENT]->(p)
      WITH p, collect(
        CASE WHEN m IS NULL THEN NULL ELSE { machineId: m.machine_id, model: m.model, evidence: r.evidence } END
      ) AS rawFitment
      WITH p, [x IN rawFitment WHERE x IS NOT NULL] AS fitment
      WHERE size(fitment) > 0
      RETURN p.part_number AS partNumber, p.part_id AS partId, fitment
    `),
  )

  const byPartNumber = {}
  for (const record of result.records) {
    const partNumber = record.get('partNumber')
    const fitment = record.get('fitment')
    byPartNumber[partNumber] = {
      partId: record.get('partId'),
      compatibleMachines: fitment.map((f) => ({
        machineId: f.machineId,
        model: f.model,
        level: EVIDENCE_TO_LEVEL[f.evidence] || 'CATEGORY',
      })),
    }
  }
  return byPartNumber
}
