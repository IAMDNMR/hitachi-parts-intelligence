import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import test, { describe } from 'node:test'

import { findCatalogueMatchId } from '../pages/PartsStore/intelligenceMatch.ts'

/**
 * Parts Intelligence -> existing Select Part convergence.
 *
 * The React components themselves (PartsIntelligence.tsx, GraphInsights.tsx)
 * call fetch() against the FastAPI backend and render cards/tabs; this
 * project's test harness (node:test over plain data/logic modules — see
 * partsStore.test.mjs) has no DOM/React-rendering setup, so those are not
 * exercised here to avoid fabricating a rendering test that doesn't really
 * run. What IS tested is the pure convergence logic: given a Parts
 * Intelligence candidate's part number, does the Parts Store resolve to the
 * SAME catalogue entry the normal search would — the one canonical Part
 * selection path required by the spec.
 */
describe('Parts Intelligence -> canonical Part selection', () => {
  const products = [
    { id: 'battery-1', partNumber: '4663907' },
    { id: 'battery-2', partNumber: '4621541' },
  ]

  test('resolves to the existing catalogue product when the part number is present', () => {
    assert.equal(findCatalogueMatchId(products, '4663907'), 'battery-1')
  })

  test('returns null (never a fabricated product) when the part number is not in the catalogue view', () => {
    assert.equal(findCatalogueMatchId(products, 'PT-999-NOT-REAL'), null)
  })

  test('returns null for a missing/empty part number rather than guessing', () => {
    assert.equal(findCatalogueMatchId(products, null), null)
    assert.equal(findCatalogueMatchId(products, undefined), null)
    assert.equal(findCatalogueMatchId(products, ''), null)
  })
})

/**
 * Question catalogue - Phase 10E. The UI reads verified questions from Aura via
 * GET /api/v1/intelligence/catalog (loaded from this CSV), so the CSV is the
 * single source of truth. Only its own shape and verification flags are tested.
 */
describe('Parts Intelligence question catalogue (CSV source of truth)', () => {
  const csvPath = path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    '../../docs/data/parts_intelligence/HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv',
  )
  const lines = readFileSync(csvPath, 'utf8').trim().split(String.fromCharCode(10))
  const header = lines[0].split(',')
  const col = (n) => header.indexOf(n)
  // question_template never contains a comma, so a plain split is safe.
  const rows = lines.slice(1).map((l) => {
    const c = l.replace(String.fromCharCode(13), '').split(',')
    return { id: c[col('question_id')], category: c[col('category')], text: c[col('question_template')], enabled: c[col('enabled')], verified: c[col('verified')] }
  })

  test('has questions in every column-complete row', () => {
    assert.ok(rows.length >= 25, `got ${rows.length}`)
    for (const r of rows) assert.ok(r.id && r.category && r.text, `incomplete row ${r.id}`)
  })

  test('no duplicate question ids or text', () => {
    assert.equal(rows.length, new Set(rows.map((r) => r.id)).size)
    assert.equal(rows.length, new Set(rows.map((r) => r.text)).size)
  })

  test('every enabled question has been verified against a real answer', () => {
    for (const r of rows.filter((x) => x.enabled === 'TRUE')) assert.equal(r.verified, 'TRUE', `${r.id} enabled but unverified`)
  })
})
