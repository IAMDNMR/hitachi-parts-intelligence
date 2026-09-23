import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import {
  MACHINES,
  VISUAL_CATEGORIES,
  categoryById,
  groupsInCategory,
  machineById,
  machinesInCategory,
} from '../data/machineCatalogue.ts'

/**
 * The machine universe the Machinery section draws.
 *
 * machineCatalogue.js is generated from the frozen workbook and the image
 * manifest, so these are not tests of hand-written data — they are the
 * invariants the SECTION depends on. Each one has a way of quietly breaking:
 *
 *  - a category with no machines renders an empty screen with no error;
 *  - a machine whose visualCategory matches no category vanishes from the site
 *    entirely while still being present in the data;
 *  - Special Applications carries three different demolition products that all
 *    share the base model code ZX250-7, so labelling tiles by model produces
 *    three identical tiles;
 *  - an image path that points at an archive master rather than a web rendition
 *    costs 20 MB on one band.
 *
 * The generator is not imported here on purpose: these assert the shape of what
 * it produced, which is what the components actually read.
 */
describe('machine catalogue', () => {
  test('has exactly the seven visual categories, in order', () => {
    assert.deepEqual(
      VISUAL_CATEGORIES.map((c) => c.id),
      ['mini', 'medium', 'large', 'wheeled', 'special', 'wheel-loaders', 'dump-trucks'],
    )
  })

  test('five categories are excavator subcategories and two are not', () => {
    const exc = VISUAL_CATEGORIES.filter((c) => c.parent === 'Excavators').map((c) => c.id)
    assert.deepEqual(exc, ['mini', 'medium', 'large', 'wheeled', 'special'])
    assert.deepEqual(
      VISUAL_CATEGORIES.filter((c) => c.parent !== 'Excavators').map((c) => c.parent),
      ['Wheel Loaders', 'Rigid Dump Trucks'],
    )
  })

  test('every category contains machines', () => {
    for (const c of VISUAL_CATEGORIES) {
      assert.ok(machinesInCategory(c.id).length > 0, `${c.id} is empty`)
      assert.equal(machinesInCategory(c.id).length, c.machineCount, `${c.id} count disagrees`)
    }
  })

  test('every machine belongs to a category that exists', () => {
    for (const m of MACHINES) {
      assert.ok(categoryById(m.visualCategory), `${m.id} -> unknown ${m.visualCategory}`)
    }
  })

  test('the categories partition the machines exactly', () => {
    const counted = VISUAL_CATEGORIES.reduce((n, c) => n + machinesInCategory(c.id).length, 0)
    assert.equal(counted, MACHINES.length)
    assert.equal(MACHINES.length, 77)
  })

  test('machine ids are unique and resolvable', () => {
    assert.equal(new Set(MACHINES.map((m) => m.id)).size, MACHINES.length)
    for (const m of MACHINES) assert.equal(machineById(m.id)?.id, m.id)
  })

  test('every machine has at least one official image', () => {
    const without = MACHINES.filter((m) => m.images.length === 0).map((m) => m.model)
    assert.deepEqual(without, [], `machines with no image: ${without.join(', ')}`)
  })

  test('no image points at an archive master — only web renditions', () => {
    for (const m of MACHINES) {
      for (const img of m.images) {
        assert.match(img.src, /-(?:480|960|1600|full)\.jpg$/, `${m.model} serves ${img.src}`)
        assert.ok(img.srcset && img.srcset.includes('w'), `${m.model} has no srcset`)
      }
    }
  })

  test('Special Applications tiles are distinguishable from one another', () => {
    const labels = machinesInCategory('special').map((m) => m.displayLabel)
    assert.equal(new Set(labels).size, labels.length, 'two special-application tiles read the same')
    /* Three demolition products share the base code ZX250-7; the label has to
       carry more than the model or the reader sees the same tile three times. */
    const shared = machinesInCategory('special').filter((m) => m.model === 'ZX250-7')
    assert.equal(shared.length, 3)
    assert.equal(new Set(shared.map((m) => m.displayLabel)).size, 3)
  })

  test('Special Applications groups cover all of its machines', () => {
    const grouped = groupsInCategory('special').flatMap((g) => g.machines)
    assert.equal(grouped.length, machinesInCategory('special').length)
    for (const g of groupsInCategory('special')) assert.ok(g.label, 'a special group has no heading')
  })

  test('every other category is a single ungrouped list', () => {
    for (const c of VISUAL_CATEGORIES.filter((x) => x.id !== 'special')) {
      const groups = groupsInCategory(c.id)
      assert.equal(groups.length, 1)
      assert.equal(groups[0].label, null)
    }
  })

  test('a multi-model page declares every code it covers', () => {
    for (const m of MACHINES) {
      assert.equal(m.modelCount, m.modelsCovered.length)
      assert.ok(m.modelsCovered.includes(m.model), `${m.id} omits its own model`)
    }
    const multi = MACHINES.filter((m) => m.modelCount > 1)
    assert.ok(multi.length > 0, 'the catalogue lost its multi-model pages')
  })

  test('every category hero is a real image from one of its own machines', () => {
    for (const c of VISUAL_CATEGORIES) {
      assert.ok(c.heroImage, `${c.id} has no hero image`)
      const own = new Set(machinesInCategory(c.id).flatMap((m) => m.images.map((i) => i.src)))
      assert.ok(own.has(c.heroImage.src), `${c.id} hero belongs to another category`)
    }
  })
})
