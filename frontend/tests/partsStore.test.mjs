import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { partsCatalogue } from '../data/partsCatalogue.js'
import { partsStoreCatalogue } from '../data/partsStoreCatalogue.js'
import { MACHINES } from '../data/machineCatalogue.js'
import { groupForCategory, levelLabel, relationshipFor } from '../pages/PartsStore/compatibility.js'

/**
 * Two catalogues, two different jobs. partsCatalogue.js is the homepage's
 * curated 16-part showcase — PartsShowcase.jsx iterates it directly to drive
 * a numbered scroll rail, so it must never grow past what that rail can
 * carry. partsStoreCatalogue.js is the Parts Store's full catalogue: that
 * same 16 (minus the superseded traction-battery placeholder, and with 3
 * curated batteries standing in for the workbook's 20) plus every real
 * product-line/family part and every real attachment read straight from
 * HITACHI_AFTERSALES_ECOM_GRAPH_MASTER.xlsx.
 *
 * Nothing here may be invented — a price, a stock count, a part number, a
 * fitment, or a product that doesn't exist in the source data at all — so
 * these tests hold both catalogues to that line. A part with no `image`
 * field is correct and intentional: it means no real, verified, on-brand
 * photo could be found, and the UI shows "Visual pending" rather than a
 * wrong or unverified one.
 */
describe('partsCatalogue (homepage showcase)', () => {
  test('has exactly the 16 approved parts', () => {
    assert.equal(partsCatalogue.length, 16)
  })

  test('no part states a price or a stock count', () => {
    for (const part of partsCatalogue) {
      assert.equal('price' in part, false, `${part.id} declares a price`)
      assert.equal('stock' in part, false, `${part.id} declares stock`)
    }
  })

  test('every part image, where present, is a real project asset — never a fabricated product photo', () => {
    for (const part of partsCatalogue) {
      if (!part.image) continue
      assert.match(part.image, /assets\/.+\.(webp|jpg|png)$/, `${part.id} image is not a project asset`)
    }
  })

  test('all showcase parts with static visuals carry verified OEM assets', () => {
    const battery = partsCatalogue.find((p) => p.id === 'traction-battery')
    const reman = partsCatalogue.find((p) => p.id === 'remanufactured-components')
    assert.ok(battery && battery.image, 'traction-battery has a verified OEM asset')
    assert.ok(reman && reman.image, 'remanufactured-components has a verified OEM asset')
  })
})

describe('partsStoreCatalogue (Parts Store)', () => {
  test('is the homepage catalogue (minus the superseded battery placeholder) plus real workbook records — nothing invented', () => {
    // 15 base (16 - traction-battery) + 3 curated batteries + 14 new family
    // parts + 13 attachments = 45. Every id below must trace to a real
    // 4_PARTS, 5_MACHINE_PARTS, or 3_ATTACHMENTS row — there is no fixed
    // "target count" this is padded out to.
    assert.equal(partsStoreCatalogue.length, 45)
    assert.equal(
      partsStoreCatalogue.some((p) => p.id === 'traction-battery'),
      false,
      'the vague traction-battery placeholder should be gone, replaced by the curated real batteries',
    )
  })

  test('no duplicate ids', () => {
    const ids = partsStoreCatalogue.map((p) => p.id)
    assert.equal(ids.length, new Set(ids).size)
  })

  test('no part states a price or a stock count', () => {
    for (const part of partsStoreCatalogue) {
      assert.equal('price' in part, false, `${part.id} declares a price`)
      assert.equal('stock' in part, false, `${part.id} declares stock`)
    }
  })

  test('every part image, where present, is a real project asset — never a fabricated product photo', () => {
    for (const part of partsStoreCatalogue) {
      if (!part.image) continue
      assert.match(part.image, /assets\/.+\.(webp|jpg|png)$/, `${part.id} image is not a project asset`)
    }
  })

  test('every fitment row names a machine that actually exists — never an invented or stale id', () => {
    const machineIds = new Set(MACHINES.map((m) => m.id))
    for (const part of partsStoreCatalogue) {
      for (const row of part.fitment || []) {
        assert.ok(machineIds.has(row.machineId), `${part.id} fitment names "${row.machineId}", which matches no machine`)
        assert.ok(
          ['EXACT MODEL', 'MODEL/RANGE', 'CATEGORY'].includes(row.level),
          `${part.id} fitment row for ${row.machineId} has an unrecognised level "${row.level}"`,
        )
      }
    }
  })

  test('the 3 curated batteries carry their published OEM part number; nothing else invents one', () => {
    const batteries = partsStoreCatalogue.filter((p) => p.id.startsWith('battery-'))
    assert.equal(batteries.length, 3)
    for (const battery of batteries) {
      assert.ok(battery.partNumber, `${battery.id} has no part number`)
      assert.notEqual(battery.partNumber, 'NOT PUBLICLY STATED')
    }
  })

  test('product-line/family parts omit partNumber rather than filling in a placeholder', () => {
    // The workbook states "NOT PUBLICLY STATED" for these; the UI's own
    // "Not supplied" fallback (DetailDrawer) is the honest way to show that,
    // not a literal placeholder string carried through the data.
    const families = [
      'hitachi-genuine-parts', 'hitachi-2genuine-parts', 'hitachi-selected-parts', 'hitachi-performance-parts',
      'genuine-oil-filter', 'genuine-fuel-filter', 'genuine-undercarriage',
      'genuine-hydraulic-oil-multi', 'zx-w-axle-oil', 'adblue-def', 'genuine-paint',
    ]
    for (const id of families) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `${id} should exist in the catalogue`)
      assert.equal(part.partNumber, undefined, `${id} should not carry a part number`)
    }
  })

  test('all 13 attachments in 3_ATTACHMENTS are represented, none invents a part number', () => {
    const attachments = [
      'backhoe-bucket', 'loading-shovel-bucket', 'wheel-loader-bucket', 'hydraulic-breaker', 'quick-coupler',
      'get-mini-compact', 'get-medium-range', 'bradken-get', 'mining-bucket-bradken-get',
      'grapple', 'hook', 'fork', 'tilt-bucket',
    ]
    for (const id of attachments) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `${id} should exist in the catalogue`)
      assert.equal(part.partNumber, undefined, `${id} should not carry a part number`)
    }
  })

  test('12 of the 13 attachments carry real fitment; Tilt bucket carries none rather than an invented one', () => {
    const withFitment = [
      'backhoe-bucket', 'loading-shovel-bucket', 'wheel-loader-bucket', 'hydraulic-breaker', 'quick-coupler',
      'get-mini-compact', 'get-medium-range', 'bradken-get', 'mining-bucket-bradken-get',
      'grapple', 'hook', 'fork',
    ]
    for (const id of withFitment) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part.fitment && part.fitment.length > 0, `${id} should have at least one real fitment row`)
    }
    const tilt = partsStoreCatalogue.find((p) => p.id === 'tilt-bucket')
    assert.ok(tilt, 'tilt-bucket should still be a catalogue product')
    assert.equal(tilt.fitment, undefined)
    assert.equal(relationshipFor(tilt, MACHINES[0]).level, 'general')
  })

  test('all 13 attachments carry an individually-verified photorealistic image asset', () => {
    const allAttachments = [
      'backhoe-bucket', 'loading-shovel-bucket', 'wheel-loader-bucket', 'hydraulic-breaker', 'quick-coupler',
      'get-mini-compact', 'get-medium-range', 'bradken-get', 'mining-bucket-bradken-get',
      'grapple', 'hook', 'fork', 'tilt-bucket',
    ]
    for (const id of allAttachments) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part.image, `${id} should carry an image asset`)
      assert.ok(part.imageSource, `${id} should declare an image source`)
      assert.doesNotMatch(part.imageSource, /Visual pending|placeholder/i)
    }
  })

  test('every product carries a verified photorealistic image', () => {
    for (const part of partsStoreCatalogue) {
      assert.ok(part.image, `${part.id} is missing an image asset`)
      assert.ok(part.imageSource, `${part.id} is missing an imageSource`)
      assert.doesNotMatch(part.imageSource, /Visual pending|placeholder/i, `${part.id} still has placeholder/pending`)
    }
  })

  test('every attachment folds into the Attachments filter bucket, distinguished by its own type', () => {
    const attachmentParts = partsStoreCatalogue.filter((p) => p.category.startsWith('Attachments'))
    assert.equal(attachmentParts.length, 13)
    for (const part of attachmentParts) {
      assert.equal(groupForCategory(part.category), 'Attachments')
      assert.ok(part.type, `${part.id} should state its attachment type`)
    }
  })

  test('no product exists that is absent from 4_PARTS, 5_MACHINE_PARTS, and 3_ATTACHMENTS alike', () => {
    // A regression guard for the specific failure this project hit once
    // already: a batch of plausible-sounding "expanded components" (control
    // valves, swing motors, radiators, cabin parts...) added straight into
    // the generated file with invented part numbers and invented fitment,
    // none of it backed by the workbook. If the catalogue count or these
    // specific ids ever reappear, that regression is back.
    const neverInvented = [
      'main-control-valve', 'swing-motor', 'travel-motor', 'turbocharger',
      'track-roller', 'carrier-roller', 'front-idler', 'drive-sprocket', 'track-shoe',
      'heavy-duty-rock-bucket', 'trenching-bucket', 'grading-bucket', 'hydraulic-shear',
      'operator-seat-suspension', 'joystick-control-lever', 'cab-display-monitor', 'cabin-air-filter',
      'hydraulic-oil-tank', 'tank-filler-caps-breathers', 'hydraulic-hose-assembly',
      'hydraulic-cylinder-seal-kit', 'pin-bushing-linkage-kit',
      'engine-radiator', 'hydraulic-oil-cooler', 'water-pump-assembly', 'alternator-assembly',
    ]
    const ids = new Set(partsStoreCatalogue.map((p) => p.id))
    for (const id of neverInvented) {
      assert.equal(ids.has(id), false, `${id} is not backed by any workbook sheet and must not be in the catalogue`)
    }
  })
})

describe('relationshipFor', () => {
  const exactMachine = MACHINES.find((m) => m.id === 'MC-044') // ZX10U-6
  const rangeMachine = MACHINES.find((m) => m.id === 'MC-033') // ZX210LC-7
  const wheelLoader = MACHINES.find((m) => m.id === 'MC-065') // ZW160-7
  const dumpTruck = MACHINES.find((m) => m.visualCategory === 'dump-trucks')
  const miniExcavator = MACHINES.find((m) => m.id === 'MC-053') // ZX65USB-6, no PT-001 fitment

  const exactBattery = partsStoreCatalogue.find((p) => p.id === 'battery-4663907') // PT-001
  const mixedBattery = partsStoreCatalogue.find((p) => p.id === 'battery-4391629') // PT-012: exact for some, range for MC-033
  const coolant = partsStoreCatalogue.find((p) => p.id === 'genuine-coolant') // PT-036, category-level
  const reman = partsStoreCatalogue.find((p) => p.id === 'remanufactured-components') // PT-024, excludes dump trucks
  const hydraulicCylinder = partsStoreCatalogue.find((p) => p.id === 'hydraulic-cylinder') // no fitment data at all

  test('with no machine selected, every part reads as a neutral prompt rather than a compatibility claim', () => {
    const rel = relationshipFor(exactBattery, null)
    assert.equal(rel.level, 'general')
    assert.match(rel.text, /select a machine/i)
  })

  test('an exact-model relationship is only reported for a machine actually named in that row', () => {
    assert.equal(relationshipFor(exactBattery, exactMachine).level, 'exact')
    assert.equal(relationshipFor(exactBattery, miniExcavator).level, 'general')
  })

  test('the same part can be exact for one machine and model-range for another — the real data does this', () => {
    assert.equal(relationshipFor(mixedBattery, rangeMachine).level, 'range')
    assert.doesNotMatch(relationshipFor(mixedBattery, rangeMachine).text, /exact/i)
  })

  test('a category-level relationship applies broadly but is never shown as verified fitment', () => {
    const rel = relationshipFor(coolant, wheelLoader)
    assert.equal(rel.level, 'category')
    assert.match(rel.text, /not published as verified fitment/i)
  })

  test('the reman family (74 of 77 machines) excludes rigid dump trucks honestly', () => {
    assert.ok(dumpTruck, 'fixture requires a dump truck in the catalogue')
    assert.equal(relationshipFor(reman, dumpTruck).level, 'general')
    assert.equal(relationshipFor(reman, wheelLoader).level, 'category')
  })

  test('a part with no fitment data at all is never reported as incompatible', () => {
    // hydraulic-cylinder predates the workbook import and carries no
    // fitment field; that is a data gap, not evidence of a mismatch.
    const rel = relationshipFor(hydraulicCylinder, wheelLoader)
    assert.equal(rel.level, 'general')
    assert.doesNotMatch(rel.text, /no confirmed compatibility/i)
  })

  test('every level relationshipFor can return has a display label', () => {
    for (const level of ['exact', 'range', 'category', 'general']) {
      assert.ok(levelLabel[level], `no label for level "${level}"`)
    }
  })
})

describe('groupForCategory', () => {
  test('folds every lubricant sub-category into one Lubricants filter bucket', () => {
    assert.equal(groupForCategory('Lubricants / Drivetrain'), 'Lubricants')
    assert.equal(groupForCategory('Lubricants / Maintenance'), 'Lubricants')
    assert.equal(groupForCategory('Lubricants / Engine'), 'Lubricants')
    assert.equal(groupForCategory('Lubricants / Cooling'), 'Lubricants')
  })

  test('folds every attachment sub-category into one Attachments filter bucket', () => {
    assert.equal(groupForCategory('Attachments / Bucket'), 'Attachments')
    assert.equal(groupForCategory('Attachments / Ground Engaging Tools'), 'Attachments')
    assert.equal(groupForCategory('Attachments / Material Handling'), 'Attachments')
  })

  test('leaves other categories as the workbook states them', () => {
    assert.equal(groupForCategory('Hydraulics'), 'Hydraulics')
    assert.equal(groupForCategory('Wheel Loader / Drivetrain'), 'Wheel Loader / Drivetrain')
  })
})
