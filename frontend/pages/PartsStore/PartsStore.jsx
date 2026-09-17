import { useEffect, useMemo, useState } from 'react'
import './PartsStore.css'

import { partsStoreCatalogue } from '../../data/partsStoreCatalogue'
import { FRAMES_PER_PART } from '../../data/partsCatalogue'
import { MACHINES, VISUAL_CATEGORIES } from '../../data/machineCatalogue'
import { PartIcon } from '../../sections/PartsShowcase/PartIcons'
import { groupForCategory, levelLabel, relationshipFor } from './compatibility'
import { SiteHeader } from '../../components/SiteHeader/SiteHeader'

const FRAME_MODULES = import.meta.glob('../../assets/source/section-03/parts-frames/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})
const FRAME_URLS = Object.keys(FRAME_MODULES)
  .sort()
  .map((key) => FRAME_MODULES[key])

const CART_KEY = 'hcme-parts-cart'

const categoryTabs = [
  { id: 'all', label: 'All Parts' },
  { id: 'Hydraulics', label: 'Hydraulic' },
  { id: 'Undercarriage', label: 'Undercarriage' },
  { id: 'Attachments', label: 'Attachments' },
  { id: 'Electrical', label: 'Electrical' },
  { id: 'Maintenance Parts', label: 'Filters' },
  { id: 'Lubricants', label: 'Lubricants' },
  { id: 'Drivetrain', label: 'Drivetrain' },
  { id: 'Reman / Replacement Parts', label: 'Reman' },
]

function isCategoryMatch(part, tabId, exact) {
  if (tabId === 'all') return true
  if (part.category === tabId || part.family === tabId) return true
  // An exact Part Category selection (from the sidebar) never falls back to
  // the coarse tab folding below — it means exactly this one category.
  if (exact) return false
  // Lubricants is its own bucket even though sub-names like "Lubricants /
  // Hydraulic" and "Lubricants / Drivetrain" share words with other tabs.
  if (tabId === 'Lubricants') return part.category.includes('Lubricant')
  if (part.category.includes('Lubricant')) return false
  if (tabId === 'Hydraulics') return part.category.includes('Hydraulic')
  if (tabId === 'Attachments') return part.category.startsWith('Attachments')
  if (tabId === 'Electrical') return part.category.includes('Electrical') || part.category.includes('Electric')
  if (tabId === 'Drivetrain') {
    return (
      part.category.includes('Drivetrain') ||
      part.category.includes('Axle') ||
      part.category.includes('Transmission') ||
      part.category.includes('Powertrain')
    )
  }
  return false
}

function partImage(part, index) {
  if (part.image) return part.image
  return FRAME_URLS[index * FRAMES_PER_PART + Math.floor(FRAMES_PER_PART / 2)] || null
}

function normalize(text) {
  return String(text || '').toLowerCase()
}

// Shared by both the actual filter and the sidebar's displayed count, so the
// number next to "Rigid Dump Trucks" can never drift from what clicking it
// actually shows — a part matches a machine TYPE only via its own real
// fitment rows, never by the blanket "no data means show anyway" rule used
// for an exact single machine (that rule doesn't hold across a whole type).
function matchesMachineType(part, machineIds) {
  return Boolean(part.fitment && part.fitment.some((f) => machineIds.has(f.machineId)))
}

function productRecords() {
  return partsStoreCatalogue.map((part, index) => ({
    ...part,
    image: partImage(part, index),
    family: groupForCategory(part.category),
  }))
}

function loadCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || []
  } catch {
    return []
  }
}

export function PartsStore({ onHome }) {
  const products = useMemo(productRecords, [])
  // Neo4j enrichment for the catalogue above — additive only. Keyed by Part
  // Number, the one identifier both sides share reliably; see
  // api/_lib/enrichment.js for why fuzzy matching is never used here. An
  // empty object (the initial state, and what stays in place if the fetch
  // fails) means every part renders exactly as it always has — enrichment
  // is optional, never load-bearing.
  const [enrichment, setEnrichment] = useState({})

  useEffect(() => {
    let cancelled = false
    fetch('/api/part-enrichment')
      .then((res) => {
        if (!res.ok) throw new Error(`/api/part-enrichment responded ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (!cancelled) setEnrichment(data.enrichment || {})
      })
      .catch(() => {
        // Silent by design: Neo4j being unreachable is not a Parts Store
        // error, so it gets none of the fallback-notice UI the enrichment
        // itself would need. The catalogue already works without it.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const [query, setQuery] = useState('')
  const [machineType, setMachineType] = useState('')
  const [machineId, setMachineId] = useState('')
  const [category, setCategory] = useState('all')
  // The Part Category sidebar sets an exact single category (its raw value
  // may coincide with a coarse top-tab id, e.g. both are literally
  // "Drivetrain" — one raw part category and one folded bucket of several),
  // so it needs to opt out of the tab's broader substring folding.
  const [categoryExact, setCategoryExact] = useState(false)
  const [sort, setSort] = useState('relevance')
  const [view, setView] = useState('grid')
  const [detail, setDetail] = useState(null)
  const [cart, setCart] = useState(loadCart)

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart))
  }, [cart])

  const machineOptions = useMemo(
    () => MACHINES.filter((m) => !machineType || m.visualCategory === machineType),
    [machineType],
  )
  const selectedMachine = MACHINES.find((m) => m.id === machineId) || null
  // A machine type without a specific model narrows to parts compatible with
  // at least one machine in that type — broader than an exact model, but
  // still a real filter rather than a no-op.
  const machineTypeIds = useMemo(
    () => new Set(MACHINES.filter((m) => m.visualCategory === machineType).map((m) => m.id)),
    [machineType],
  )
  // Precomputed once for every type, so each sidebar badge shows the exact
  // product count that type's filter will produce, not the machine count.
  const machineTypeIdsByCategory = useMemo(() => {
    const map = {}
    for (const cat of VISUAL_CATEGORIES) {
      map[cat.id] = new Set(MACHINES.filter((m) => m.visualCategory === cat.id).map((m) => m.id))
    }
    return map
  }, [])

  const filtered = useMemo(() => {
    const q = normalize(query)
    const list = products.filter((p) => {
      const rel = relationshipFor(p, selectedMachine)
      const matchesQuery =
        !q ||
        normalize(p.name).includes(q) ||
        normalize(p.category).includes(q) ||
        normalize(p.partNumber).includes(q) ||
        normalize(selectedMachine?.model).includes(q)
      const matchesCategory = isCategoryMatch(p, category, categoryExact)
      let matchesMachine = true
      if (selectedMachine) {
        matchesMachine = rel.level !== 'general' || !p.fitment
      } else if (machineType) {
        // Unlike an exact machine, a machine type is a broad bucket (Mini,
        // Wheel Loaders, Rigid Dump Trucks...). A part with no fitment data
        // at all has no evidence either way for one specific machine, but
        // showing it under every single type regardless — a bucket or swing
        // bearing under "Rigid Dump Trucks" — reads as a wrong match, not an
        // honest gap. So this requires the fitment it actually has.
        matchesMachine = matchesMachineType(p, machineTypeIds)
      }
      return matchesQuery && matchesCategory && matchesMachine
    })
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      if (sort === 'category') return a.category.localeCompare(b.category)
      if (sort === 'compatibility') {
        const score = { exact: 0, range: 1, category: 2, general: 3 }
        return score[relationshipFor(a, selectedMachine).level] - score[relationshipFor(b, selectedMachine).level]
      }
      return 0
    })
  }, [category, categoryExact, machineType, machineTypeIds, products, query, selectedMachine, sort])

  const addToCart = (product) => {
    setCart((items) => {
      const existing = items.find((item) => item.id === product.id)
      if (existing) return items.map((item) => item.id === product.id ? { ...item, qty: item.qty + 1 } : item)
      return [...items, { id: product.id, name: product.name, qty: 1, machine: selectedMachine?.model || null }]
    })
  }

  const applyMachineType = (id) => {
    setMachineType(id)
    setMachineId('')
  }

  return (
    <main className="ps" id="parts-store">
      <SiteHeader
        position="sticky"
        current="parts-store"
        cartCount={cart.reduce((sum, item) => sum + item.qty, 0)}
        onBrandClick={(event) => {
          event.preventDefault()
          onHome()
        }}
      />

      <section className="ps-hero">
        <div className="ps-hero__copy">
          <p className="ps-eyebrow">Genuine Hitachi Parts</p>
          <h1>Keep your <span>world moving</span></h1>
          <p>The right parts. The right fit. Maximum uptime.</p>
          <div className="ps-search">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by part name, category or machine model..."
            />
            <button type="button" onClick={() => document.getElementById('ps-results')?.scrollIntoView({ behavior: 'smooth' })}>
              Search
            </button>
          </div>
          <div className="ps-hero__trust" aria-label="Parts Store strengths">
            <span>Genuine quality</span>
            <span>Machine-aware search</span>
            <span>Dealer-ready quote flow</span>
          </div>
        </div>

        <div className="ps-machine-finder">
          <h2>Find parts for your machine</h2>
          <label>
            Machine category
            <select value={machineType} onChange={(event) => applyMachineType(event.target.value)}>
              <option value="">All machine categories</option>
              {VISUAL_CATEGORIES.map((cat) => <option value={cat.id} key={cat.id}>{cat.label}</option>)}
            </select>
          </label>
          <label>
            Machine model
            <select value={machineId} onChange={(event) => setMachineId(event.target.value)}>
              <option value="">Select model</option>
              {machineOptions.map((machine) => <option value={machine.id} key={machine.id}>{machine.model}</option>)}
            </select>
          </label>
          <button type="button" onClick={() => document.getElementById('ps-results')?.scrollIntoView({ behavior: 'smooth' })}>
            Find compatible parts
          </button>
        </div>
      </section>

      <nav className="ps-cats" aria-label="Part categories">
        {categoryTabs.map((tab) => (
          <button
            type="button"
            key={tab.id}
            className={category === tab.id && !categoryExact ? 'is-active' : undefined}
            onClick={() => { setCategory(tab.id); setCategoryExact(false) }}
          >
            <span>{tab.label}</span>
            <small>{products.filter((p) => isCategoryMatch(p, tab.id)).length}</small>
          </button>
        ))}
      </nav>

      <section className="ps-body" id="ps-results">
        <aside className="ps-filters" aria-label="Filters">
          <div className="ps-panel-head">
            <h2>Filters</h2>
            <button type="button" onClick={() => { setMachineType(''); setMachineId(''); setCategory('all'); setCategoryExact(false); setQuery('') }}>Clear all</button>
          </div>
          <FilterGroup title="Machine Type">
            {VISUAL_CATEGORIES.map((cat) => (
              <label className="ps-check" key={cat.id}>
                <input type="radio" checked={machineType === cat.id} onChange={() => applyMachineType(cat.id)} />
                <span>{cat.label}</span>
                <small>{products.filter((p) => matchesMachineType(p, machineTypeIdsByCategory[cat.id])).length}</small>
              </label>
            ))}
          </FilterGroup>
          <FilterGroup title="Part Category">
            {[...new Set(products.map((p) => p.family))].map((name) => (
              <label className="ps-check" key={name}>
                <input type="radio" checked={category === name && categoryExact} onChange={() => { setCategory(name); setCategoryExact(true) }} />
                <span>{name}</span>
                <small>{products.filter((p) => p.family === name).length}</small>
              </label>
            ))}
          </FilterGroup>
          <FilterGroup title="Availability">
            <p className="ps-muted">No stock feed is available in this project. Products use request quote flow.</p>
          </FilterGroup>
        </aside>

        <div className="ps-results">
          <div className="ps-results__bar">
            <div>
              <h2>{filtered.length} parts found</h2>
              <p>{selectedMachine ? `For ${selectedMachine.model}` : 'Across the full Hitachi OEM parts catalogue'}</p>
            </div>
            <div className="ps-tools">
              <select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort parts">
                <option value="relevance">Relevance</option>
                <option value="compatibility">Compatibility</option>
                <option value="category">Category</option>
                <option value="name">Name</option>
              </select>
              <button type="button" className={view === 'grid' ? 'is-active' : undefined} onClick={() => setView('grid')}>Grid</button>
              <button type="button" className={view === 'list' ? 'is-active' : undefined} onClick={() => setView('list')}>List</button>
            </div>
          </div>

          <div className={`ps-grid ps-grid--${view}`}>
            {filtered.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                selectedMachine={selectedMachine}
                onDetail={() => setDetail(product.id)}
                onCart={() => addToCart(product)}
              />
            ))}
          </div>
        </div>
      </section>

      <TrustStrip />

      {detail && (
        <DetailDrawer
          product={products.find((p) => p.id === detail)}
          enrichment={enrichment}
          cart={cart}
          setCart={setCart}
          selectedMachine={selectedMachine}
          onClose={() => setDetail(null)}
        />
      )}
    </main>
  )
}

function FilterGroup({ title, children }) {
  return <section className="ps-filter-group"><h3>{title}</h3>{children}</section>
}

function ProductCard({ product, selectedMachine, onDetail, onCart }) {
  const relation = relationshipFor(product, selectedMachine)
  return (
    <article className="ps-card">
      <button className="ps-card__fav" type="button" aria-label="Save part">♡</button>
      <button className="ps-card__image" type="button" onClick={onDetail}>
        {product.image ? (
          <img src={product.image} alt={product.name} />
        ) : (
          <span className="ps-card__pending">
            <PartIcon name="tag" size={22} />
            Visual pending
          </span>
        )}
      </button>
      <div className="ps-card__body">
        <p className={`ps-status ps-status--${relation.level}`}>{levelLabel[relation.level]}</p>
        <h3>{product.name}</h3>
        <p>{relation.text}</p>
        <span className="ps-badge">{product.category}</span>
        {product.partNumber && <span className="ps-badge ps-badge--part">Part {product.partNumber}</span>}
      </div>
      <div className="ps-card__actions">
        <button type="button" onClick={onDetail}>Quick view</button>
        <button type="button" onClick={onCart}>Request Quote</button>
      </div>
    </article>
  )
}

function DetailDrawer({ product, enrichment, cart, setCart, selectedMachine, onClose }) {
  const rel = relationshipFor(product, selectedMachine)
  // Exact Part Number match only — see api/_lib/enrichment.js. A part with
  // no partNumber, or one Neo4j has no fitment data for, simply has nothing
  // here; the rest of this drawer is unaffected either way.
  const verified = product.partNumber ? enrichment?.[product.partNumber] : null
  return (
    <div className="ps-drawer" role="dialog" aria-modal="true">
      <button type="button" className="ps-drawer__close" onClick={onClose}>Close</button>
      <h2>{product?.name}</h2>
      <div className="ps-drawer__grid">
        <article>
          {product.image ? (
            <img src={product.image} alt={product.name} />
          ) : (
            <span className="ps-card__pending">
              <PartIcon name="tag" size={22} />
              Visual pending
            </span>
          )}
          <h3>{product.name}</h3>
          <p>{product.description}</p>
          <dl>
            <dt>Category</dt><dd>{product.category}</dd>
            {product.type && <><dt>Part type</dt><dd>{product.type}</dd></>}
            <dt>Part number</dt><dd>{product.partNumber || 'Not supplied'}</dd>
            <dt>Compatibility</dt><dd>{rel.text}</dd>
            <dt>Relationship level</dt><dd>{levelLabel[rel.level]}</dd>
            <dt>Availability</dt><dd>Quote required. No live stock feed.</dd>
            <dt>Price</dt><dd>Not supplied</dd>
            {verified && (
              <>
                <dt>Compatible machines (verified)</dt>
                <dd>{verified.compatibleMachines.map((m) => m.model).join(', ')}</dd>
              </>
            )}
          </dl>
          <button type="button" onClick={() => setCart([...cart, { id: product.id, name: product.name, qty: 1, machine: selectedMachine?.model || null }])}>Add to quote request</button>
        </article>
      </div>
    </div>
  )
}

function TrustStrip() {
  const items = ['Genuine Hitachi Parts', 'Fast Global Delivery', 'Expert Support', 'Sustainable Solutions', 'Global Network']
  return <section className="ps-trust">{items.map((item) => <div key={item}><strong>{item}</strong><span>Built for after-sales uptime.</span></div>)}</section>
}
