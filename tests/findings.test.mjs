import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { collectFindings, countConfidence, FINDING_ORDER } from '../.test-build/findings.js'
import { groundNodes, groundEdges } from '../.test-build/graph.js'

/**
 * The findings report.
 *
 * It is a client deliverable derived from the model, which means the thing
 * that matters is that it cannot drift from the model: every uncertain claim
 * in the graph appears, no certain one does, and nothing is authored twice.
 */

const findings = collectFindings(groundNodes, groundEdges)

describe('the report is derived, not written', () => {
  test('it lists every uncertain node and no confirmed one', () => {
    const expected = groundNodes
      .filter((n) => n.provenance.confidence !== 'confirmed')
      .map((n) => n.id)
      .sort()
    const got = findings.filter((f) => f.about === 'node').map((f) => f.key).sort()
    assert.deepEqual(got, expected)
  })

  test('it lists every uncertain relationship and no confirmed one', () => {
    const expected = groundEdges
      .filter((e) => e.confidence !== 'confirmed')
      .map((e) => `${e.from}->${e.to}`)
      .sort()
    const got = findings.filter((f) => f.about === 'relationship').map((f) => f.key).sort()
    assert.deepEqual(got, expected)
  })

  test('the tally adds up to the whole model', () => {
    const c = countConfidence(groundNodes, groundEdges)
    assert.equal(c.total, groundNodes.length + groundEdges.length)
    assert.equal(c.confirmed + c.open, c.total)
    assert.equal(c.open, findings.length, 'the count and the list must agree')
  })

  test('every finding can be found on the map', () => {
    /* Each one offers "Show on the map", and a link to a node that does not
       exist is worse than no link. */
    const ids = new Set(groundNodes.map((n) => n.id))
    const broken = findings.filter((f) => !ids.has(f.nodeId)).map((f) => f.key)
    assert.deepEqual(broken, [])
  })

  test('what the sources fail to answer is ranked above what we assumed', () => {
    /* The order is the argument: a box the client drew and did not route is a
       harder question for them than a step we assumed because every parts
       operation has one. */
    const rank = (c) => FINDING_ORDER.indexOf(c)
    for (let i = 1; i < findings.length; i++) {
      assert.ok(
        rank(findings[i - 1].confidence) <= rank(findings[i].confidence),
        `${findings[i - 1].confidence} should not follow ${findings[i].confidence}`,
      )
    }
    assert.equal(rank('not-supplied') < rank('assumed'), true)
  })

  test('every finding says what it claims', () => {
    const silent = findings.filter((f) => !f.title || !f.claim).map((f) => f.key)
    assert.deepEqual(silent, [], 'a finding with no claim is a row of nothing')
  })
})
