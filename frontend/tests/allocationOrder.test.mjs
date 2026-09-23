import assert from 'node:assert/strict'
import test, { describe } from 'node:test'

import { formatOrderPrice } from '../components/orderDisplay.ts'

/**
 * Phase 6 Allocation + Order UI logic tests.
 *
 * Mirrors tests/partsIntelligence.test.mjs's documented approach: this
 * project's harness (node:test over plain logic modules, esbuild-compiled
 * TS) has no DOM/React-rendering setup, so AllocationOrderPanel.tsx itself
 * is not rendered here. What IS tested is the pure, extracted pricing
 * display rule it uses — specifically the "never fabricate a price"
 * requirement (spec item 13 / item 20-21: UNKNOWN never silently becomes a
 * concrete value).
 */
describe('Order review price display never fabricates a number', () => {
  test('shows the confirmed price + currency when pricingStatus is CONFIRMED', () => {
    assert.equal(
      formatOrderPrice({ unitPrice: 42.5, currency: 'EUR', pricingStatus: 'CONFIRMED' }),
      '42.5 EUR'
    )
  })

  test('shows "Price unavailable from current source" when pricingStatus is NOT_AVAILABLE', () => {
    assert.equal(
      formatOrderPrice({ unitPrice: null, currency: null, pricingStatus: 'NOT_AVAILABLE' }),
      'Price unavailable from current source'
    )
  })

  test('never fabricates a number even if unitPrice is somehow present but status is not CONFIRMED', () => {
    assert.equal(
      formatOrderPrice({ unitPrice: 99, currency: 'EUR', pricingStatus: 'NOT_AVAILABLE' }),
      'Price unavailable from current source'
    )
  })

  test('treats a null unitPrice as unavailable regardless of status', () => {
    assert.equal(
      formatOrderPrice({ unitPrice: null, currency: 'EUR', pricingStatus: 'CONFIRMED' }),
      'Price unavailable from current source'
    )
  })
})
