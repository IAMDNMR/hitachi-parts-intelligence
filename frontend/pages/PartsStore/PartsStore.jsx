import { useEffect, useMemo, useState } from 'react'
import './PartsStore.css'

import { partsStoreCatalogue } from '../../data/partsStoreCatalogue'
import { FRAMES_PER_PART, partAttributes } from '../../data/partsCatalogue'
import { MACHINES, VISUAL_CATEGORIES } from '../../data/machineCatalogue'
import { PartIcon } from '../../sections/PartsShowcase/PartIcons'
import { DetailIcon } from './DetailIcons'
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

/**
 * The real compatible-machine list for a part, grouped by the fitment
 * evidence level, for display when no specific machine is selected. Before
 * this, the drawer's only compatibility line was "Select a machine to check
 * applicability" even for parts (most attachments, for instance) that
 * already carry a full fitment array — real data sitting unused because the
 * UI only ever read it against one chosen machine. Nothing here invents a
 * fitment fact: it only reads the array that was already there and resolves
 * each machineId to its real model via MACHINES. A part with no fitment
 * array at all still gets nothing here — that stays a genuine gap, not a
 * guess.
 */
function fitmentSummary(product) {
  if (!product.fitment || product.fitment.length === 0) return null
  const byLevel = { 'EXACT MODEL': [], 'MODEL/RANGE': [], CATEGORY: [] }
  for (const f of product.fitment) {
    const machine = MACHINES.find((m) => m.id === f.machineId)
    if (machine && byLevel[f.level]) byLevel[f.level].push(machine.model)
  }
  const groups = [
    { label: 'Exact model', models: byLevel['EXACT MODEL'] },
    { label: 'Model range', models: byLevel['MODEL/RANGE'] },
    { label: 'Category-level', models: byLevel.CATEGORY },
  ].filter((g) => g.models.length > 0)
  return groups.length > 0 ? groups : null
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
  // Three small, independent states for the quote-request flow: which panel
  // is open (cart list, or the customer-details form), and how the last
  // submit attempt went (for the form's own inline feedback — 'sending' |
  // 'error' | 'success' | null).
  const [quoteCartOpen, setQuoteCartOpen] = useState(false)
  const [quoteFormOpen, setQuoteFormOpen] = useState(false)
  const [quoteStatus, setQuoteStatus] = useState(null)
  // A small "Added to quote request" confirmation — cleared on its own
  // after a couple of seconds, same pattern for whichever button set it.
  const [toast, setToast] = useState(null)

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart))
  }, [cart])

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(null), 2200)
    return () => clearTimeout(timer)
  }, [toast])

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

  // Single path for every "add" action on the page (product card, Quick
  // View) — the card's default is qty=1; Quick View passes whatever its own
  // quantity selector is set to. Adding a part already in the cart adds to
  // its existing quantity rather than creating a second row.
  const addToCart = (product, qty = 1) => {
    setCart((items) => {
      const existing = items.find((item) => item.id === product.id)
      if (existing) return items.map((item) => item.id === product.id ? { ...item, qty: item.qty + qty } : item)
      return [
        ...items,
        {
          id: product.id,
          name: product.name,
          qty,
          machine: selectedMachine?.model || null,
          image: product.image || null,
          // Carried through to /api/quote-request so a submitted inquiry
          // can link back to the real Part node — see api/_lib/quoteRequest.js.
          partNumber: product.partNumber || null,
        },
      ]
    })
    setToast(`Added ${product.name} to quote request`)
  }

  const applyMachineType = (id) => {
    setMachineType(id)
    setMachineId('')
  }

  const submitQuoteRequest = async (details) => {
    setQuoteStatus('sending')
    try {
      const res = await fetch('/api/quote-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...details, items: cart }),
      })
      if (!res.ok) throw new Error('request failed')
      // Cleared immediately so the same items can't be submitted twice —
      // the success message stays on screen briefly (QuoteRequestForm's
      // own 'success' view) before everything closes.
      setCart([])
      setQuoteStatus('success')
      setTimeout(() => {
        setQuoteFormOpen(false)
        setQuoteCartOpen(false)
        setQuoteStatus(null)
      }, 1600)
    } catch {
      // Neo4j being unreachable (or any other failure) never loses the
      // cart or breaks the store — the form stays open with a plain error
      // so the visitor can just try Send again.
      setQuoteStatus('error')
    }
  }

  return (
    <main className="ps" id="parts-store">
      <SiteHeader
        position="sticky"
        current="parts-store"
        cartCount={cart.reduce((sum, item) => sum + item.qty, 0)}
        onCartClick={() => setQuoteCartOpen(true)}
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
          selectedMachine={selectedMachine}
          onAddToCart={addToCart}
          onClose={() => setDetail(null)}
        />
      )}

      {quoteCartOpen && !quoteFormOpen && (
        <QuoteCartPanel
          cart={cart}
          setCart={setCart}
          onClose={() => setQuoteCartOpen(false)}
          onRequestQuote={() => setQuoteFormOpen(true)}
        />
      )}

      {quoteFormOpen && (
        <QuoteRequestForm
          cart={cart}
          status={quoteStatus}
          onClose={() => {
            setQuoteFormOpen(false)
            setQuoteStatus(null)
          }}
          onSubmit={submitQuoteRequest}
        />
      )}

      {toast && <div className="ps-toast" role="status">{toast}</div>}
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

function DetailDrawer({ product, enrichment, selectedMachine, onAddToCart, onClose }) {
  const [qty, setQty] = useState(1)
  const rel = relationshipFor(product, selectedMachine)
  // Exact Part Number match only — see api/_lib/enrichment.js. A part with
  // no partNumber, or one Neo4j has no fitment data for, simply has nothing
  // here; the rest of this drawer is unaffected either way.
  const verified = product.partNumber ? enrichment?.[product.partNumber] : null
  // Without a selected machine, rel.text is just "Select a machine to check
  // applicability" — true, but it throws away a real fitment array if the
  // part has one (most attachments and non-showcase parts do). Show that
  // real list instead when it exists; the per-machine relationshipFor
  // behaviour is untouched once a machine actually is selected.
  const summary = !selectedMachine ? fitmentSummary(product) : null

  // One real photo per part today (partsStoreCatalogue.js has never carried
  // more than one) — `images` stays an array so a future part with a real
  // multi-angle set renders a thumbnail strip automatically, without this
  // needing to change. Nothing here invents extra angles from one photo.
  const images = product.image ? [product.image] : []

  const compatibilityFacts = summary
    ? summary.map((g) => ({ key: g.label, label: `Compatible machines (${g.label})`, value: g.models.join(', ') }))
    : [
        { key: 'compat', label: 'Compatibility', value: rel.text },
        { key: 'level', label: 'Relationship level', value: levelLabel[rel.level] },
      ]

  const facts = [
    { key: 'category', icon: 'category', label: 'Category', value: product.category },
    ...(product.type ? [{ key: 'type', icon: 'category', label: 'Part type', value: product.type }] : []),
    { key: 'partNumber', icon: 'partNumber', label: 'Part number', value: product.partNumber || 'Not supplied' },
    ...compatibilityFacts.map((f) => ({ ...f, icon: 'compatibility' })),
    ...(verified
      ? [{
          key: 'verified',
          icon: 'compatibility',
          label: 'Compatible machines (verified)',
          value: verified.compatibleMachines.map((m) => m.model).join(', '),
        }]
      : []),
    { key: 'availability', icon: 'availability', label: 'Availability', value: 'Quote required. No live stock feed.' },
    // Genuine Hitachi OEM parts are priced through an authorised dealer, not
    // published publicly (hitachicm.com's own parts pages carry none) — see
    // the commit that added this drawer for how that was checked, not
    // assumed. "Not supplied" states that plainly rather than leaving it to
    // look like an oversight.
    { key: 'price', icon: 'price', label: 'Price', value: 'Not supplied — genuine parts are dealer-quoted, not publicly listed' },
  ]

  return (
    <div className="ps-modal-overlay" role="presentation" onClick={onClose}>
      <div className="ps-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="ps-modal__close" onClick={onClose} aria-label="Close">×</button>

        <header className="ps-modal__header">
          <p className="ps-modal__eyebrow">Part details</p>
          <h2 className="ps-modal__title">{product?.name}</h2>
          <p className="ps-modal__lede">{product.description}</p>
        </header>

        <div className="ps-modal__body">
          <div className="ps-modal__media">
            <div className="ps-modal__image">
              {images.length > 0 ? (
                <img src={images[0]} alt={product.name} />
              ) : (
                <span className="ps-card__pending">
                  <PartIcon name="tag" size={22} />
                  Visual pending
                </span>
              )}
            </div>

            {images.length > 1 && (
              <div className="ps-modal__thumbs">
                {images.map((src, i) => (
                  <button type="button" key={src} className={i === 0 ? 'is-active' : undefined}>
                    <img src={src} alt="" />
                  </button>
                ))}
              </div>
            )}

            {product.attributes?.length > 0 && (
              <ul className="ps-modal__attrs">
                {product.attributes.map((key) => {
                  const attr = partAttributes[key]
                  if (!attr) return null
                  return (
                    <li key={key}>
                      <PartIcon name={attr.icon} size={18} />
                      <span>{attr.label}</span>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="ps-modal__info">
            <h3>Key information</h3>
            <ul className="ps-modal__facts">
              {facts.map((f) => (
                <li key={f.key}>
                  <span className="ps-modal__fact-icon"><DetailIcon name={f.icon} size={18} /></span>
                  <span className="ps-modal__fact-text">
                    <strong>{f.label}</strong>
                    <span>{f.value}</span>
                  </span>
                </li>
              ))}
            </ul>

            <div className="ps-modal__help">
              <DetailIcon name="help" size={20} />
              <div>
                <strong>Need help finding the right part?</strong>
                <p>Select a machine model or contact us for expert support.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="ps-qty-row">
          <span>Quantity</span>
          <span className="ps-qty">
            <button type="button" onClick={() => setQty((q) => Math.max(1, q - 1))} disabled={qty <= 1} aria-label="Decrease quantity">−</button>
            <span aria-live="polite">{qty}</span>
            <button type="button" onClick={() => setQty((q) => q + 1)} aria-label="Increase quantity">+</button>
          </span>
        </div>

        <footer className="ps-modal__footer">
          <div className="ps-modal__brand">
            <strong>HITACHI</strong>
            <span>Genuine parts<br />Greater uptime</span>
          </div>
          <button type="button" onClick={() => onAddToCart(product, qty)}>
            Add to quote request →
          </button>
        </footer>
      </div>
    </div>
  )
}

/**
 * The cart's own view — reachable now that the header's Cart badge is
 * clickable (components/SiteHeader). Reuses the Quick View's modal shell
 * (.ps-modal*) rather than a new visual system, per "use the existing
 * UI/design wherever possible". Lists exactly what's already in `cart` —
 * no price, no stock, nothing this project doesn't actually have.
 */
function QuoteCartPanel({ cart, setCart, onClose, onRequestQuote }) {
  const removeItem = (id) => setCart(cart.filter((item) => item.id !== id))
  const changeQty = (id, delta) =>
    setCart(cart.map((item) => (item.id === id ? { ...item, qty: Math.max(1, item.qty + delta) } : item)))

  return (
    <div className="ps-modal-overlay" role="presentation" onClick={onClose}>
      <div className="ps-modal ps-modal--narrow" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="ps-modal__close" onClick={onClose} aria-label="Close">×</button>
        <header className="ps-modal__header">
          <p className="ps-modal__eyebrow">Quote cart</p>
          <h2 className="ps-modal__title">{cart.length === 0 ? 'No parts added yet' : `${cart.length} part${cart.length === 1 ? '' : 's'} added`}</h2>
        </header>

        {cart.length > 0 && (
          <ul className="ps-quote-cart-list">
            {cart.map((item) => (
              <li key={item.id}>
                <span className="ps-quote-cart-list__image">
                  {item.image ? <img src={item.image} alt="" /> : <PartIcon name="tag" size={18} />}
                </span>
                <span className="ps-quote-cart-list__info">
                  <strong>{item.name}</strong>
                  <small>
                    Part number: {item.partNumber || '—'}
                    {item.machine && ` · For ${item.machine}`}
                  </small>
                </span>
                <span className="ps-qty ps-qty--compact">
                  <button type="button" onClick={() => changeQty(item.id, -1)} disabled={item.qty <= 1} aria-label={`Decrease quantity of ${item.name}`}>−</button>
                  <span aria-live="polite">{item.qty}</span>
                  <button type="button" onClick={() => changeQty(item.id, 1)} aria-label={`Increase quantity of ${item.name}`}>+</button>
                </span>
                <button type="button" className="ps-quote-cart-list__remove" onClick={() => removeItem(item.id)} aria-label={`Remove ${item.name}`}>Remove</button>
              </li>
            ))}
          </ul>
        )}

        <footer className="ps-modal__footer">
          <button type="button" className="ps-modal__secondary" onClick={onClose}>Keep browsing</button>
          <button type="button" onClick={onRequestQuote} disabled={cart.length === 0}>Request Quote →</button>
        </footer>
      </div>
    </div>
  )
}

/**
 * The customer-details form. Submitting calls /api/quote-request, which
 * writes (:PartsInquiry)-[:REQUESTS]->(:RequestedPart)-[:FOR_PART]->(:Part)
 * — see api/_lib/quoteRequest.js. Only name and email are required; phone
 * and note are asked for but optional, since requiring them would block a
 * real inquiry over information this project has no way to insist on.
 */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Field-level validation — name/email/phone required, note is not. */
function validateQuoteDetails({ name, email, phone }) {
  const errors = {}
  if (!name.trim()) errors.name = 'Name is required.'
  if (!email.trim()) errors.email = 'Email is required.'
  else if (!EMAIL_PATTERN.test(email.trim())) errors.email = 'Enter a valid email address.'
  if (!phone.trim()) errors.phone = 'Phone is required.'
  return errors
}

function QuoteRequestForm({ cart, status, onClose, onSubmit }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [note, setNote] = useState('')
  // Errors only ever show after the visitor has tried to submit once —
  // showing "Name is required" before they've typed anything reads as the
  // form scolding them for existing.
  const [attempted, setAttempted] = useState(false)

  const errors = validateQuoteDetails({ name, email, phone })
  const hasErrors = Object.keys(errors).length > 0

  const handleSubmit = (event) => {
    event.preventDefault()
    setAttempted(true)
    if (hasErrors || cart.length === 0) return
    onSubmit({ name, email, phone, note })
  }

  if (status === 'success') {
    return (
      <div className="ps-modal-overlay" role="presentation">
        <div className="ps-modal ps-modal--narrow ps-modal--success" role="dialog" aria-modal="true">
          <p className="ps-modal__eyebrow">Request quote</p>
          <h2 className="ps-modal__title">Quote request sent</h2>
          <p className="ps-modal__lede">We&rsquo;ve received your request and will be in touch shortly.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="ps-modal-overlay" role="presentation" onClick={onClose}>
      <div className="ps-modal ps-modal--narrow" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="ps-modal__close" onClick={onClose} aria-label="Close">×</button>
        <header className="ps-modal__header">
          <p className="ps-modal__eyebrow">Request quote</p>
          <h2 className="ps-modal__title">Your details</h2>
        </header>

        <ul className="ps-quote-form__summary">
          {cart.map((item) => (
            <li key={item.id}>{item.name} × {item.qty}</li>
          ))}
        </ul>

        <form className="ps-quote-form" onSubmit={handleSubmit} noValidate>
          <label>
            Name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
              aria-invalid={attempted && Boolean(errors.name)}
            />
            {attempted && errors.name && <span className="ps-quote-form__field-error">{errors.name}</span>}
          </label>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              aria-invalid={attempted && Boolean(errors.email)}
            />
            {attempted && errors.email && <span className="ps-quote-form__field-error">{errors.email}</span>}
          </label>
          <label>
            Phone
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              autoComplete="tel"
              aria-invalid={attempted && Boolean(errors.phone)}
            />
            {attempted && errors.phone && <span className="ps-quote-form__field-error">{errors.phone}</span>}
          </label>
          <label>
            Purpose / Note
            <textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
          </label>

          {status === 'error' && (
            <p className="ps-quote-form__error">
              We couldn&rsquo;t send your request right now. Please try again.
            </p>
          )}

          <footer className="ps-modal__footer">
            <button type="button" className="ps-modal__secondary" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={status === 'sending'}>
              {status === 'sending' ? 'Sending…' : 'Send Request →'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}

function TrustStrip() {
  const items = ['Genuine Hitachi Parts', 'Fast Global Delivery', 'Expert Support', 'Sustainable Solutions', 'Global Network']
  return <section className="ps-trust">{items.map((item) => <div key={item}><strong>{item}</strong><span>Built for after-sales uptime.</span></div>)}</section>
}
