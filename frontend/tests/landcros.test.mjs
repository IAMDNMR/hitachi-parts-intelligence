import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { LANDCROS } from '../data/landcros.js'
import { MACHINES } from '../data/machineCatalogue.js'

/**
 * LANDCROS is hand-written data, so these hold it to the same rules as the
 * generated catalogue. Each one guards a way the band could quietly start
 * telling the reader something untrue:
 *
 *  - a concept creeping into the catalogue would put a machine nobody can buy
 *    on the floor next to the ones they can;
 *  - a source outside HCME Europe breaks the project's one-region rule;
 *  - an image that is not a web rendition is either invented or an archive
 *    master served whole.
 */
const EU = 'https://www.hitachicm.com/eu/en/'

describe('LANDCROS', () => {
  test('there are exactly the two concept machines HCME has shown', () => {
    assert.deepEqual(LANDCROS.concepts.map((c) => c.name), ['LANDCROS One', 'LANDCROS Mini'])
  })

  test('no concept is part of the 77-machine catalogue', () => {
    const names = new Set(MACHINES.map((m) => m.name.toLowerCase()))
    for (const c of LANDCROS.concepts) {
      assert.ok(!names.has(c.name.toLowerCase()), `${c.name} is in the catalogue`)
      assert.ok(!MACHINES.some((m) => /landcros/i.test(m.name)), 'a catalogue machine is named LANDCROS')
    }
  })

  test('every source is an official HCME Europe page', () => {
    const sources = [
      LANDCROS.rebrandSource,
      LANDCROS.connect.href,
      ...LANDCROS.concepts.map((c) => c.source),
      ...LANDCROS.timeline.map((t) => t.source),
    ]
    for (const s of sources) assert.ok(s.startsWith(EU), `${s} is not on ${EU}`)
  })

  test('every photograph is a web rendition from the LANDCROS library', () => {
    for (const c of LANDCROS.concepts) {
      assert.ok(c.gallery.length > 0, `${c.name} has no photographs`)
      for (const g of c.gallery) {
        assert.match(g.src, /^\/machines\/LANDCROS\/.+-1600\.jpg$/)
        assert.ok(g.alt && g.alt.length > 10, `${g.src} has no real alt text`)
      }
    }
  })

  test('every fact names an icon the band can draw', () => {
    /* The set drawn by SPEC_ICONS in LandcrosBand.jsx. An unknown key renders
       an empty orange disc with nothing in it. */
    const drawn = new Set(['event', 'power', 'operation', 'award', 'weight', 'view'])
    for (const c of LANDCROS.concepts) {
      for (const s of c.specs) assert.ok(drawn.has(s.icon), `${c.name} / ${s.label}: no icon "${s.icon}"`)
    }
  })

  test('the timeline runs in date order and ends at the April 2027 rebrand', () => {
    const dates = LANDCROS.timeline.map((t) => t.date)
    assert.deepEqual([...dates].sort(), dates)
    assert.equal(dates.at(-1), '2027-04')
  })
})
