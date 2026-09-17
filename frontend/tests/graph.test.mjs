import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { groundNodes, groundEdges, CONFIDENCE_LABELS, NODE_TYPE_LABELS } from '../.test-build/graph.js'

/**
 * The model itself.
 *
 * These are the invariants the graph has to hold for the page to be honest,
 * and every one of them has been broken at some point during this project's
 * life — an edge naming a node that no longer existed, an entity nothing
 * produced, a reveal list that disagreed with the edges in fifty-two places.
 * None of them can be caught by TypeScript, because they are properties of
 * the data rather than of its shape.
 */

const ids = new Set(groundNodes.map((n) => n.id))

describe('the graph is well formed', () => {
  test('no two nodes share an id', () => {
    const seen = new Set()
    const dupes = groundNodes.filter((n) => (seen.has(n.id) ? true : (seen.add(n.id), false)))
    assert.deepEqual(dupes.map((n) => n.id), [])
  })

  test('every edge joins two nodes that exist', () => {
    const dangling = groundEdges
      .filter((e) => !ids.has(e.from) || !ids.has(e.to))
      .map((e) => `${e.from} -> ${e.to}`)
    assert.deepEqual(dangling, [])
  })

  test('no edge is declared twice', () => {
    const seen = new Set()
    const dupes = []
    for (const e of groundEdges) {
      const key = `${e.from}->${e.to}`
      if (seen.has(key)) dupes.push(key)
      seen.add(key)
    }
    assert.deepEqual(dupes, [])
  })

  test('no node is stranded with no relationship at all', () => {
    const touched = new Set(groundEdges.flatMap((e) => [e.from, e.to]))
    const alone = groundNodes.filter((n) => !touched.has(n.id)).map((n) => n.id)
    assert.deepEqual(alone, [])
  })

  test('every node declares a confidence the legend can name', () => {
    const unknown = groundNodes
      .filter((n) => !(n.provenance.confidence in CONFIDENCE_LABELS))
      .map((n) => `${n.id}: ${n.provenance.confidence}`)
    assert.deepEqual(unknown, [])
  })

  test('every node declares a type the legend can name', () => {
    const unknown = groundNodes
      .filter((n) => !(n.type in NODE_TYPE_LABELS))
      .map((n) => `${n.id}: ${n.type}`)
    assert.deepEqual(unknown, [])
  })
})

describe('what the model claims about itself', () => {
  test('every data entity traces back to a business process', () => {
    /**
     * A real invariant — an entity nothing in the business reaches is an
     * entity nobody creates — but NOT, it turns out, a test for the Returns
     * Order gap, and the comment here said otherwise until it was checked.
     *
     * Deleting the process → system edge that closed that gap leaves this
     * test green, because Returns Order still traces to a process through
     * D365's other three process edges. The original gap was that no process
     * raised a returns order SPECIFICALLY, and "specifically" is carried by
     * the label on an edge, not by the shape of the graph. Nothing structural
     * can catch it; the test below, which asserts the parts chain actually
     * closes, is what guards that work.
     */
    const feeds = new Map()
    for (const e of groundEdges) {
      if (!feeds.has(e.to)) feeds.set(e.to, [])
      feeds.get(e.to).push(e.from)
    }
    const byId = new Map(groundNodes.map((n) => [n.id, n]))

    const tracesToAProcess = (id) => {
      const seen = new Set([id])
      const queue = [id]
      while (queue.length) {
        const at = queue.shift()
        for (const from of feeds.get(at) ?? []) {
          if (seen.has(from)) continue
          const node = byId.get(from)
          if (node && (node.type === 'process' || node.type === 'pillar')) return true
          seen.add(from)
          queue.push(from)
        }
      }
      return false
    }

    const unreached = groundNodes
      .filter((n) => n.type === 'entity' && !tracesToAProcess(n.id))
      .map((n) => n.id)
    assert.deepEqual(unreached, [], 'an entity nothing in the business does is an entity nobody creates')
  })

  test('the parts chain closes — a part fitted comes back as a core', () => {
    /* The core loop, asserted as a path rather than as four edges, so it
       survives the chain being lengthened and fails if any link is dropped.
       This is what guards the closed-loop work. */
    const after = new Map()
    for (const e of groundEdges) {
      if (!after.has(e.from)) after.set(e.from, [])
      after.get(e.from).push(e.to)
    }
    const reaches = (from, to) => {
      const seen = new Set([from])
      const queue = [from]
      while (queue.length) {
        const at = queue.shift()
        for (const next of after.get(at) ?? []) {
          if (next === to) return true
          if (seen.has(next)) continue
          seen.add(next)
          queue.push(next)
        }
      }
      return false
    }
    assert.ok(reaches('p-installation', 'p-core-return'), 'a fitted part must be able to come back')
    assert.ok(reaches('p-core-return', 'p-reman'), 'a returned core must reach remanufacture')
    assert.ok(reaches('p-reman', 'p-inventory'), 'a remanufactured unit must return to stock')
    assert.ok(reaches('p-inventory', 'p-inventory'), 'and the chain must therefore be a loop')
  })

  test('the only cycle is the core loop that closes the parts chain', () => {
    const after = new Map()
    for (const e of groundEdges) {
      if (e.from === e.to) continue
      if (!after.has(e.from)) after.set(e.from, [])
      after.get(e.from).push(e.to)
    }
    const colour = new Map()
    const cycles = []
    const walk = (at, path) => {
      colour.set(at, 'open')
      for (const next of after.get(at) ?? []) {
        if (colour.get(next) === 'open') cycles.push([...path, at, next])
        else if (!colour.has(next)) walk(next, [...path, at])
      }
      colour.set(at, 'done')
    }
    for (const n of groundNodes) if (!colour.has(n.id)) walk(n.id, [])

    assert.equal(cycles.length, 1, 'a second cycle means the map has grown a loop nobody designed')
    const loop = cycles[0]
    assert.equal(loop.at(-1), 'p-inventory')
    assert.ok(loop.includes('p-reman'), 'the loop should close through remanufacture')
    assert.ok(loop.includes('p-core-return'), 'and open at the core coming off the machine')
  })

  test('nothing states a price, a real part number or a machine reading', () => {
    /* The model describes an architecture, not a transaction. Numbers that
       look like data are how a diagram quietly stops being trustworthy. */
    const prose = groundNodes
      .flatMap((n) => [n.label, n.summary, n.role ?? '', ...(n.detail ?? [])])
      .join(' ')
    assert.doesNotMatch(prose, /[€$£]\s?\d/, 'a price appeared in the model')
    assert.doesNotMatch(prose, /\b\d{3}-\d{3}-\d{3}\b/, 'a part number appeared in the model')
    assert.doesNotMatch(prose, /\b\d+\s?(hours|hrs|litres|kg|rpm)\b/i, 'a machine reading appeared')
  })
})
