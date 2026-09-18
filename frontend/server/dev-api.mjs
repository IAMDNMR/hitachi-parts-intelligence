import { createServer } from 'node:http'
import partEnrichmentHandler from '../api/part-enrichment.js'
import quoteRequestHandler from '../api/quote-request.js'

/**
 * Local stand-in for Vercel's serverless function runtime.
 *
 * Vite's dev server only serves the frontend; it has no notion of the
 * `api/` directory Vercel builds into functions at deploy time. This tiny
 * server hosts the exact same handlers so `npm run dev` exercises the real
 * Neo4j -> API -> React path, not a stand-in. vite.config.js proxies
 * `/api/*` here during development only; production traffic never touches
 * this file — Vercel parses a JSON request body into req.body itself,
 * which is why that parsing is done here explicitly and nowhere in the
 * handlers.
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

function readJsonBody(req) {
  return new Promise((resolve) => {
    let data = ''
    req.on('data', (chunk) => { data += chunk })
    req.on('end', () => {
      if (!data) return resolve({})
      try {
        resolve(JSON.parse(data))
      } catch {
        resolve({})
      }
    })
  })
}

const routes = {
  '/api/part-enrichment': partEnrichmentHandler,
  '/api/quote-request': quoteRequestHandler,
}

const server = createServer(async (req, res) => {
  const handler = routes[req.url]
  if (!handler) {
    res.statusCode = 404
    res.end('Not found')
    return
  }
  if (req.method === 'POST') {
    req.body = await readJsonBody(req)
  }
  handler(req, toVercelStyleResponse(res))
})

server.listen(PORT, () => {
  console.log(`Dev API listening on http://localhost:${PORT}`)
})
