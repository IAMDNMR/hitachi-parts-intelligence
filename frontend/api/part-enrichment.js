import { getEnrichmentByPartNumber } from './_lib/enrichment.js'

/**
 * GET /api/part-enrichment — verified Neo4j information for the EXISTING
 * Parts Store catalogue, keyed by Part Number for an exact (never fuzzy)
 * match on the frontend. This does not replace, list, or count parts — the
 * static catalogue (frontend/data/partsStoreCatalogue.js) remains the sole
 * source of which products exist, their images, and their identity. If this
 * endpoint is unreachable, the Parts Store must keep working exactly as it
 * does today; nothing here is load-bearing for the catalogue itself.
 */
export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  try {
    const enrichment = await getEnrichmentByPartNumber()
    res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=300')
    res.status(200).json({ enrichment })
  } catch (error) {
    // Never echo the error's own message — it could reveal connection
    // details. Vercel's own function logs are where that detail belongs.
    console.error('GET /api/part-enrichment failed:', error.message)
    res.status(502).json({ error: 'Enrichment data is temporarily unavailable.' })
  }
}
