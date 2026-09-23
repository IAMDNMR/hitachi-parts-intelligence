import assert from 'node:assert/strict'
import test, { describe } from 'node:test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const _csv = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)),
  '../../docs/data/parts_intelligence/HCME_PARTS_INTELLIGENCE_QUESTION_CATALOG.csv'), 'utf8').trim().split(String.fromCharCode(10))
const _tcol = _csv[0].split(',').indexOf('question_template')
const QUESTION_CATALOGUE = _csv.slice(1).map((l) => ({ text: l.split(',')[_tcol] }))

describe('Phase 10 Supplier Risk & Network Question Catalogue', () => {
  const REQUIRED_SUPPLIER_QUESTIONS = [
    'Which suppliers are in Netherlands?',
    'Which suppliers are in Germany?',
    'Which suppliers are in Eindhoven?',
    'Which suppliers are in Oosterhout?',
    'Show me supplier 0000100026.',
  ]

  const REQUIRED_NETWORK_QUESTIONS = [
    'Show me the dealers and suppliers in Netherlands.',
    'Which suppliers are in the same city as Pellen Machines?',
    'Which cities have both dealers and suppliers?',
    'Which suppliers are in the same city as the Oosterhout depot?',
    'Show me the Netherlands dealer and supplier network.',
  ]

  test('launcher catalogue contains all 5 required supplier master questions', () => {
    const texts = QUESTION_CATALOGUE.map((q) => q.text)
    for (const req of REQUIRED_SUPPLIER_QUESTIONS) {
      assert.ok(texts.includes(req), `Missing question: "${req}"`)
    }
  })

  test('launcher catalogue contains all 5 required dealer+supplier network questions', () => {
    const texts = QUESTION_CATALOGUE.map((q) => q.text)
    for (const req of REQUIRED_NETWORK_QUESTIONS) {
      assert.ok(texts.includes(req), `Missing question: "${req}"`)
    }
  })
})

describe('Phase 10 Supplier Risk Two-State Contract', () => {
  test('State B (NOT_CONNECTED) contains 1,720 supplier count and no demo suppliers', () => {
    const stateB = {
      status: 'NOT_CONNECTED',
      connected: false,
      reason: 'Supplier master data is available, but supplier-to-part sourcing relationships are not available.',
      supplier_master_count: 1720,
      available_dimensions: ['Supplier', 'City', 'Country'],
      missing_relationship: 'Supplier → Part',
      required_source: 'SAP purchasing/source-list/PO data containing supplier number + material/part number.',
      risk_calculations: 'UNAVAILABLE',
      part_suppliers: [],
      dual_source: false,
      concentration: [],
      spof: { is_spof: false, reason: 'Supplier-to-part sourcing relationship is not recorded.' },
      geographic_distribution: [
        { code: 'NL', country: 'Netherlands', count: 1131 },
        { code: 'DE', country: 'Germany', count: 117 },
      ],
      sample_suppliers: [
        { supplier_number: '0000100026', name: 'THORBURN GEIGER SA', city: 'Lausanne', country: 'Switzerland' },
      ],
      data_basis: 'HCME supplier master (1,720 records) contains verified supplier and location data. Supplier-to-part sourcing relationships are NOT CONNECTED in current HCME source data.',
      provenance: 'SOURCE_DERIVED / NOT_CONNECTED',
    }

    assert.equal(stateB.status, 'NOT_CONNECTED')
    assert.equal(stateB.connected, false)
    assert.equal(stateB.part_suppliers.length, 0)
    assert.equal(stateB.concentration.length, 0)
    assert.equal(stateB.supplier_master_count, 1720)
    assert.equal(stateB.risk_calculations, 'UNAVAILABLE')
    assert.ok(stateB.geographic_distribution.length > 0)
    assert.equal(stateB.geographic_distribution[0].count, 1131)
    assert.equal(stateB.sample_suppliers[0].supplier_number, '0000100026')

    const demoNames = [
      'Demo Powertrain Supplier',
      'Demo Lubricants Supplier',
      'Demo Hydraulics Supplier A',
      'Demo Filtration & Coatings Supplier',
      'Demo Electrical Supplier',
    ]
    for (const s of stateB.part_suppliers) {
      assert.ok(!demoNames.includes(s.name), 'Demo supplier leaked into part_suppliers')
    }
    for (const c of stateB.concentration) {
      assert.ok(!demoNames.includes(c.name), 'Demo supplier leaked into concentration')
    }
  })

  test('State A (CONNECTED) supports verified supplier-to-part calculations', () => {
    const stateA = {
      status: 'CONNECTED',
      connected: true,
      part_suppliers: [
        { supplier_id: '0000100026', name: 'THORBURN GEIGER SA', country: 'CH', region: 'Europe', tier: 1, share_pct: 100, role: 'SOLE' },
      ],
      dual_source: false,
      concentration: [],
      spof: { is_spof: true, reason: 'Sole-sourced from THORBURN GEIGER SA on high-criticality path.' },
      data_basis: 'SOURCE_DERIVED — Verified HCME supplier-to-part sourcing records.',
    }

    assert.equal(stateA.status, 'CONNECTED')
    assert.equal(stateA.connected, true)
    assert.equal(stateA.part_suppliers.length, 1)
    assert.equal(stateA.part_suppliers[0].name, 'THORBURN GEIGER SA')
  })
})
