import test from 'node:test'
import assert from 'node:assert/strict'
import { OOSTERHOUT_DEPOT, calculateHaversineKm, estimateRoadKm } from '../components/CheckoutWizard/geo.ts'

test('CheckoutWizard geo distance calculation', async (t) => {
  await t.test('calculates straight-line distance from Oosterhout to Auer GmbH (Matrei, Austria)', () => {
    // Matrei am Brenner coords: 47.119042, 11.450451
    const dist = calculateHaversineKm(
      OOSTERHOUT_DEPOT.latitude,
      OOSTERHOUT_DEPOT.longitude,
      47.119042,
      11.450451
    )
    // Straight-line distance should be ~692.9 km
    assert.ok(dist >= 680 && dist <= 710, `Expected distance around 692.9 km, got ${dist}`)
  })

  await t.test('calculates estimated road distance with 1.25x European routing factor', () => {
    const straightKm = 692.92
    const roadKm = estimateRoadKm(straightKm)
    const expected = Math.round(692.92 * 1.25 * 100) / 100
    assert.equal(roadKm, expected)
    assert.ok(roadKm > straightKm, 'Road distance must be greater than straight-line distance')
  })

  await t.test('returns 0 km for identical coordinates', () => {
    const dist = calculateHaversineKm(51.6431, 4.8569, 51.6431, 4.8569)
    assert.equal(dist, 0)
  })
})
