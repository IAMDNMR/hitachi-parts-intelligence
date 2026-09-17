import { createServer } from 'node:http'
import partEnrichmentHandler from '../api/part-enrichment.js'

/**
 * Local stand-in for Vercel's serverless function runtime.
 *
 * Vite's dev server only serves the frontend; it has no notion of the
 * `api/` directory Vercel builds into functions at deploy time. This tiny
 * server hosts the exact same handler (api/part-enrichment.js) so
 * `npm run dev` exercises the real Neo4j -> API -> React enrichment path,
 * not a stand-in. vite.config.js proxies `/api/*` here during development
 * only; production traffic never touches this file.
 */
const PORT = Number(process.env.DEV_API_PORT) || 8787

function toVercelStyleResponse(res) {
  return {
    status(code) {
      res.statusCode = code
      return this
    },
    setHeader(name, value) {
      res.setHeader(name, value)
      return this
    },
    json(body) {
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify(body))
    },
  }
}

const server = createServer((req, res) => {
  if (req.url === '/api/part-enrichment') {
    partEnrichmentHandler(req, toVercelStyleResponse(res))
    return
  }
  res.statusCode = 404
  res.end('Not found')
})

server.listen(PORT, () => {
  console.log(`Dev API listening on http://localhost:${PORT}`)
})
