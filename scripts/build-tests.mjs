import { mkdirSync, rmSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'

/**
 * Bundles the TypeScript the tests exercise into plain ESM that `node --test`
 * can import.
 *
 * Node cannot import .ts directly and the project has no test framework. It
 * does not need one for this: the two modules worth testing hardest — the
 * layout engine and the graph model — are pure, so they need a bundler and an
 * assertion library, and esbuild is already here as part of Vite while
 * `node:assert` ships with the runtime. Adding Vitest would mean a dependency
 * and a config file to check two functions that take data and return data.
 */
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = join(root, '.test-build')

rmSync(out, { recursive: true, force: true })
mkdirSync(out, { recursive: true })

/* One call per entry with an explicit outfile, so the results land flat.
   A single call with `outdir` mirrors the source tree instead — the files
   come out at utils/layout.js and data/graph.js, which makes the import
   paths in the tests describe the layout of src/ground rather than the
   layout of the build. */
const entries = {
  'layout.js': 'src/ground/utils/layout.ts',
  'graph.js': 'src/ground/data/graph.ts',
}

for (const [name, from] of Object.entries(entries)) {
  await build({
    entryPoints: [join(root, from)],
    outfile: join(out, name),
    bundle: true,
    format: 'esm',
    // No DOM here. layout.ts measures label widths through a canvas context
    // when one exists and falls back to an estimate when it does not, which
    // is the path these tests take.
    platform: 'neutral',
    logLevel: 'warning',
  })
}
