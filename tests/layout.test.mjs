import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { layoutGraph } from '../.test-build/layout.js'
import { groundNodes, groundEdges } from '../.test-build/graph.js'

/**
 * The layout engine.
 *
 * The highest-risk code in the project: five hundred lines of ranking,
 * crossing reduction and connector routing that nothing checked, whose
 * failures are visual and therefore only ever found by looking. Every
 * assertion here stands for something that has actually gone wrong on screen
 * — boxes printed on top of each other, connectors drawn through the middle
 * of a node's name, a camera handed a graph height that did not match the
 * one it was fitting.
 */

const near = new Map()
for (const e of groundEdges) {
  if (e.from === e.to) continue
  if (!near.has(e.from)) near.set(e.from, new Set())
  if (!near.has(e.to)) near.set(e.to, new Set())
  near.get(e.from).add(e.to)
  near.get(e.to).add(e.from)
}

/** What the page actually draws: a route, plus what the selection touches. */
function view(route) {
  const sel = route.at(-1)
  return new Set([...route, ...(near.get(sel) ?? [])])
}

function overlaps(l) {
  const bad = []
  for (let i = 0; i < l.nodes.length; i++) {
    for (let j = i + 1; j < l.nodes.length; j++) {
      const a = l.nodes[i]
      const b = l.nodes[j]
      if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) {
        bad.push(`${a.node.id} / ${b.node.id}`)
      }
    }
  }
  return bad
}

const VIEWS = {
  'the opening': view(['machine-sold', 'sales', 'after-sales']),
  'a domain': view(['after-sales', 'parts']),
  'a process chain': view(['parts', 'p-requirement', 'p-identification', 'p-availability', 'p-ordering']),
  'a system fanning out': view(['p-identification', 'sys-d365']),
  'a data entity': view(['sys-d365', 'e-part']),
  'the core loop': new Set([
    'p-inventory', 'p-shipment', 'p-goods-receipt', 'dealer',
    'p-installation', 'p-core-return', 'p-core-assessment', 'p-reman',
  ]),
  'every node at once': new Set(groundNodes.map((n) => n.id)),
}

describe('layoutGraph places a readable picture', () => {
  for (const [name, visible] of Object.entries(VIEWS)) {
    test(name, () => {
      const l = layoutGraph(groundNodes, groundEdges, visible, () => true)

      assert.equal(l.nodes.length, visible.size, 'every visible node must be placed')
      assert.deepEqual(overlaps(l), [], 'boxes must not be drawn on top of each other')

      for (const p of l.nodes) {
        assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y), `${p.node.id} has no position`)
        assert.ok(p.w > 0 && p.h > 0, `${p.node.id} has no size`)
      }

      for (const e of l.edges) {
        assert.doesNotMatch(e.path, /NaN|Infinity|undefined/, `${e.edge.from}->${e.edge.to} is malformed`)
      }

      // The camera fits against these two numbers; if they understate the
      // drawing, part of the graph is laid out beyond the edge of the frame.
      const right = Math.max(...l.nodes.map((p) => p.x + p.w))
      const bottom = Math.max(...l.nodes.map((p) => p.y + p.h))
      assert.ok(right <= l.width + 0.5, 'reported width must cover the nodes')
      assert.ok(bottom <= l.height + 0.5, 'reported height must cover the nodes')
    })
  }
})

describe('the things that have broken before', () => {
  test('a cycle in the visible set degrades instead of throwing', () => {
    /* Ranking is a topological sort, and the core loop made the model cyclic
       for the first time. The fallback had never run. */
    const l = layoutGraph(groundNodes, groundEdges, VIEWS['the core loop'], () => true)
    assert.equal(l.nodes.length, 8)
    assert.deepEqual(overlaps(l), [])
  })

  test('rows are only as tall as what they hold', () => {
    /* Every row used to be pitched for the tallest kind of node that exists,
       so a chain of 42px process steps paid for 54px rows. Height is what the
       camera runs out of on these views, so the waste came off the labels. */
    const chain = layoutGraph(groundNodes, groundEdges, VIEWS['a process chain'], () => true)
    const rows = chain.levels.length
    const perRow = chain.height / rows
    assert.ok(perRow < 100, `a row of process steps should cost under 100px, got ${perRow.toFixed(0)}`)
  })

  test('an empty view does not produce a broken canvas', () => {
    const l = layoutGraph(groundNodes, groundEdges, new Set(), () => false)
    assert.deepEqual(l.nodes, [])
    assert.ok(l.width > 0 && l.height > 0, 'a zero-sized canvas divides by zero in the camera')
  })

  test('a single node is centred rather than placed at the origin', () => {
    const l = layoutGraph(groundNodes, groundEdges, new Set(['uptime']), () => false)
    assert.equal(l.nodes.length, 1)
    assert.equal(l.nodes[0].x, 0)
    assert.ok(l.width >= l.nodes[0].w)
  })

  test('a node dragged by the reader keeps its displacement', () => {
    const visible = VIEWS['a domain']
    const base = layoutGraph(groundNodes, groundEdges, visible, () => true)
    const moved = layoutGraph(groundNodes, groundEdges, visible, () => true, new Map([['parts', { dx: 40, dy: -12 }]]))
    const before = base.byId.get('parts')
    const after = moved.byId.get('parts')
    assert.equal(after.x - before.x, 40)
    assert.equal(after.y - before.y, -12)
  })
})
