import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { classifyCartItem, isFulfilmentEligible, demoPartReferenceFor, isDemoPartReference } from '../pages/PartsStore/eligibility.ts'
import { partsStoreCatalogue } from '../data/partsStoreCatalogue.ts'

describe('Parts Store Data-Truth Eligibility Contract (Phase 11)', () => {
  test('the 3 curated OEM batteries are verified and checkout-eligible', () => {
    const verifiedIds = ['battery-4663907', 'battery-4391629', 'battery-4354442']
    for (const id of verifiedIds) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `Expected ${id} to exist in partsStoreCatalogue`)
      const res = classifyCartItem(part)
      assert.equal(res.classification, 'VERIFIED', `${id} should be classified as VERIFIED`)
      assert.equal(res.isEligible, true, `${id} must be eligible for checkout`)
      assert.equal(res.actionType, 'CHECKOUT')
      assert.equal(isFulfilmentEligible(part), true)
    }
  })

  test('PT-054 with placeholder sequence "12345678" is quarantined and checkout-disabled', () => {
    const pt054 = partsStoreCatalogue.find((p) => p.id === 'pt-054-led-work-light-group')
    assert.ok(pt054, 'Expected pt-054 to exist')
    const res = classifyCartItem(pt054)
    assert.equal(res.classification, 'UNVERIFIED_SOURCE_MISMATCH')
    assert.equal(res.isEligible, false)
    assert.equal(res.actionType, 'DEMO_CHECKOUT')
    assert.equal(isFulfilmentEligible(pt054), false)
  })

  test('PT-055 with Yanmar starter "114362-77011" is quarantined and checkout-disabled', () => {
    const pt055 = partsStoreCatalogue.find((p) => p.id === 'pt-055-starter-motor-24v')
    assert.ok(pt055, 'Expected pt-055 to exist')
    const res = classifyCartItem(pt055)
    assert.equal(res.classification, 'UNVERIFIED_SOURCE_MISMATCH')
    assert.equal(res.isEligible, false)
    assert.equal(res.actionType, 'DEMO_CHECKOUT')
    assert.equal(isFulfilmentEligible(pt055), false)
  })

  test('PT-044 through PT-048 internal references require verification and cannot checkout', () => {
    const internalRefs = [
      'pt-044-main-control-valve',
      'pt-045-main-hydraulic-pump',
      'pt-046-stagev-diesel-engine',
      'pt-047-swing-bearing',
      'pt-048-final-drive-motor',
    ]
    for (const id of internalRefs) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `Expected ${id} to exist`)
      const res = classifyCartItem(part)
      assert.equal(res.classification, 'UNVERIFIED_INTERNAL_REF', `${id} should be UNVERIFIED_INTERNAL_REF`)
      assert.equal(res.isEligible, false, `${id} must not be checkout-eligible`)
      assert.equal(res.actionType, 'DEMO_CHECKOUT')
      assert.equal(isFulfilmentEligible(part), false)
    }
  })

  test('ambiguous assemblies require serial lookup and route to identification modal', () => {
    const ambiguousIds = ['hydraulic-cylinder', 'fuel-injection-pump']
    for (const id of ambiguousIds) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `Expected ${id} to exist`)
      const res = classifyCartItem(part)
      assert.equal(res.classification, 'AMBIGUOUS', `${id} should be AMBIGUOUS`)
      assert.equal(res.isEligible, false)
      assert.equal(res.actionType, 'IDENTIFY_SERIAL')
      assert.equal(isFulfilmentEligible(part), false)
    }
  })

  test('resolving an ambiguous cylinder with OEM assembly part number makes it checkout-eligible', () => {
    const resolvedItem = {
      id: 'hydraulic-cylinder',
      name: 'Boom Cylinder Assembly (Left/Standard)',
      partNumber: '4410244',
      provenanceStatus: 'REAL',
      category: 'Hydraulics',
    }
    const res = classifyCartItem(resolvedItem)
    assert.equal(res.classification, 'VERIFIED')
    assert.equal(res.isEligible, true)
    assert.equal(res.actionType, 'CHECKOUT')
    assert.equal(isFulfilmentEligible(resolvedItem), true)
  })

  test('product families and attachments are never checkout-eligible without serial specification', () => {
    const familiesAndAttachments = [
      'hitachi-genuine-parts',
      'genuine-oil-filter',
      'backhoe-bucket',
      'quick-coupler',
    ]
    for (const id of familiesAndAttachments) {
      const part = partsStoreCatalogue.find((p) => p.id === id)
      assert.ok(part, `Expected ${id} to exist`)
      const res = classifyCartItem(part)
      assert.equal(res.isEligible, false)
      assert.notEqual(res.actionType, 'CHECKOUT')
      assert.equal(isFulfilmentEligible(part), false)
    }
  })

  test('EVERY catalogue item can move into the order workflow; unverified ones use a labelled DEMO reference and are never green', () => {
    for (const part of partsStoreCatalogue) {
      const res = classifyCartItem(part)
      if (res.actionType === 'CHECKOUT') {
        assert.equal(res.demoPartReference, null)
        assert.equal(res.isEligible, true)
      } else {
        assert.ok(['DEMO_CHECKOUT', 'IDENTIFY_SERIAL'].includes(res.actionType), `${part.id}: dead action ${res.actionType}`)
        assert.equal(res.isEligible, false, `${part.id}: an unverified item must never be marked verified`)
        assert.ok(isDemoPartReference(res.demoPartReference), `${part.id}: no labelled demo reference`)
        assert.ok(!/verif(y|ication)/i.test(res.buttonLabel), `${part.id}: button must not ask for verification`)
      }
      assert.ok(res.badgeLabel && res.buttonLabel && res.partNumberDisplay)
      assert.ok(!/undefined|null|NaN|\[object/i.test(`${res.badgeLabel} ${res.partNumberDisplay} ${res.note ?? ''}`), `${part.id}: unsafe text`)
    }
  })

  test('demo references are labelled, deterministic and never look like an OEM number', () => {
    const item = { id: 'wheel-loader-bucket', name: 'Wheel loader bucket', qty: 1, machine: null, image: null, partNumber: null }
    assert.equal(demoPartReferenceFor(item), 'DEMO-WHEEL-LOADER-BUCKET')
    assert.equal(demoPartReferenceFor({ ...item, partNumber: '4621008' }), 'DEMO-4621008')
    assert.equal(isDemoPartReference('4621008'), false)
  })
})
