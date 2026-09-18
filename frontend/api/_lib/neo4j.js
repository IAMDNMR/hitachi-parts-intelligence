import neo4j from 'neo4j-driver'
import { config as loadEnv } from 'dotenv'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * Neo4j Aura connection, shared by every API route.
 *
 * In production, NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_DATABASE
 * are Vercel project environment variables — set once in the Vercel
 * dashboard, never committed. Locally, they don't exist in process.env yet,
 * so this falls back to the repository's own neo4j/.env (git-ignored,
 * created once during the Aura import work) the same way the Python import
 * scripts (neo4j/scripts/aura_import.py) already do. Nothing here ever
 * reads, logs, or returns the credential values themselves.
 */
const __dirname = dirname(fileURLToPath(import.meta.url))
loadEnv({ path: resolve(__dirname, '../../../neo4j/.env') })

let driver

function getDriver() {
  if (driver) return driver
  const uri = process.env.NEO4J_URI
  const username = process.env.NEO4J_USERNAME
  const password = process.env.NEO4J_PASSWORD
  if (!uri || !username || !password) {
    throw new Error('Neo4j credentials are not configured (NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD).')
  }
  driver = neo4j.driver(uri, neo4j.auth.basic(username, password))
  return driver
}

/** Runs `work(session)` in a managed read session and always closes it. */
export async function withSession(work) {
  const session = getDriver().session({
    database: process.env.NEO4J_DATABASE || 'neo4j',
    defaultAccessMode: neo4j.session.READ,
  })
  try {
    return await work(session)
  } finally {
    await session.close()
  }
}

/**
 * Same as withSession, but for the handful of routes that actually write
 * (today: quote-request.js, creating a PartsInquiry). Every other route in
 * this project is read-only by design; this exists so that stays visible at
 * a glance rather than every route defaulting to write access.
 */
export async function withWriteSession(work) {
  const session = getDriver().session({
    database: process.env.NEO4J_DATABASE || 'neo4j',
    defaultAccessMode: neo4j.session.WRITE,
  })
  try {
    return await work(session)
  } finally {
    await session.close()
  }
}
