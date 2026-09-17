import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import test, { describe } from 'node:test'

import { MACHINES, VISUAL_CATEGORIES, categoryById, machinesInCategory } from '../data/machineCatalogue.js'
import { infoRows, nameParts, storyLine } from '../sections/Machinery/showcase.js'

const onDisk = (url) => existsSync(new URL(`../public${url}`, import.meta.url))

/**
 * The model showcase shows one machine per screen, and everything it says
 * about that machine comes from these functions. They are held to the rule the
 * whole project runs on: nothing invented, nothing the workbook marks as
 * unknown shown as if it were known.
 */
describe('model showcase', () => {
  test('every machine has its own isolated hero asset, and the files exist', () => {
    for (const m of MACHINES) {
      assert.ok(m.hero, `${m.id} has no hero asset`)
      assert.ok(onDisk(m.hero.src), `${m.id}: ${m.hero.src} is not on disk`)
      assert.ok(m.hero.srcset.includes(m.hero.src), `${m.id}: src is not one of its renditions`)
    }
  })

  test('facts are only ever values the workbook states', () => {
    for (const m of MACHINES) {
      for (const r of infoRows(m)) {
        assert.ok(r.value && r.value.trim(), `${m.id} ${r.key} is empty`)
        assert.doesNotMatch(r.value, /not (publicly )?stated|undefined|null/i, `${m.id} ${r.key}: ${r.value}`)
      }
    }
  })

  test('each fact carries a key the showcase draws an icon for', () => {
    const drawn = new Set(['category', 'model', 'weight', 'power'])
    for (const m of MACHINES) for (const r of infoRows(m)) assert.ok(drawn.has(r.key), `${m.id}: ${r.key}`)
  })

  test('the story line is built from the record and stays short', () => {
    for (const m of MACHINES) {
      const line = storyLine(m, categoryById(m.visualCategory))
      assert.ok(line.length > 10, `${m.id} has no line`)
      assert.doesNotMatch(line, /undefined|null|not stated/i)
      // three applications at most, then "and more"
      assert.ok(line.split(',').length <= 3, `${m.id} names too many applications: ${line}`)
    }
  })

  test('Special Applications keeps its application in front of the name', () => {
    const special = machinesInCategory('special').map(nameParts)
    assert.ok(special.filter((p) => p.kicker).length >= 10, 'most special machines lost their application')
    assert.deepEqual(nameParts({ displayLabel: 'Demolition — ZX390TC-7' }), { kicker: 'Demolition', name: 'ZX390TC-7' })
    // and the names that result are still all different from one another
    const labels = special.map((p) => `${p.kicker} ${p.name}`)
    assert.equal(new Set(labels).size, labels.length)
  })

  test('the right panel stays short: category, model, and at most two more', () => {
    for (const m of MACHINES) {
      const rows = infoRows(m)
      assert.ok(rows.length <= 4, `${m.id} has ${rows.length} rows`)
      for (const r of rows) assert.ok(r.value.length <= 44, `${m.id} ${r.key} is long: ${r.value}`)
      assert.doesNotMatch(rows.map((r) => r.value).join(' '), /\blbs?\b/, `${m.id} shows imperial units`)
    }
  })

  test('every category has something to show', () => {
    for (const c of VISUAL_CATEGORIES) assert.ok(machinesInCategory(c.id).length > 0, c.id)
  })
})
