import { mkdirSync, rmSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'

/**
 * Bundles the TypeScript the tests exercise into plain ESM that `node --test`
 * can import.
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = join(root, '.test-build')

rmSync(out, { recursive: true, force: true })
mkdirSync(out, { recursive: true })

const entries = {
  'layout.js': 'pages/TheGround/utils/layout.ts',
  'graph.js': 'pages/TheGround/data/graph.ts',
}

for (const [name, from] of Object.entries(entries)) {
  await build({
    entryPoints: [join(root, from)],
    outfile: join(out, name),
    bundle: true,
    format: 'esm',
    platform: 'node',
    logLevel: 'warning',
    external: ['neo4j-driver'],
  })
}
