import { useCallback, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from 'react'
import './OrdersPage.css'

import { SiteHeader } from '../../components/SiteHeader/SiteHeader'

/**
 * Orders — the business / operations area. Everything on this screen is read from, and written to, the existing Neo4j AuraDB through the FastAPI
 * backend: the list from GET /orders, the lifecycle from GET /orders/{id}/operations, every step from POST /orders/{id}/ops/{action}.
 * Nothing is kept in the browser (no localStorage / sessionStorage); a refresh shows exactly what is stored.
 *
 * The lifecycle stepper shows the PERSISTED state of each step (done / current / pending). Which step's panel is open is a separate,
 * purely visual choice: clicking a step never changes its state.
 */

interface OrderRow {
  order_id: string
  status: string
  customer_name: string
  customer_email?: string | null
  dealer_name: string | null
  parts: { part_number: string; part_name: string | null; quantity: number }[]
  placed_at: string
}

type StepState = 'done' | 'current' | 'pending'
type StepKey = 'order' | 'allocation' | 'fulfilment' | 'shipment' | 'tracking' | 'service' | 'completed'
interface Step { key: StepKey; label: string; state: StepState; detail: string | null }

interface ShipmentEvent { id: string; event_type: string; description: string | null; location: string | null; timestamp: string | null }
interface Shipment {
  shipment_id: string
  status: string
  carrier: string | null
  tracking_number: string | null
  service_tier: string | null
  eta: string | null
  shipped_at: string | null
  delivered_at: string | null
  origin: string | null
  destination: string | null
  destination_dealer_name: string | null
  events: ShipmentEvent[]
}
interface ServiceJob {
  service_job_id: string
  status: string
  work_order_number: string | null
  dealer_name: string | null
  received_at: string | null
  started_at: string | null
  installed_at: string | null
  completed_at: string | null
  events: { id: string; event_type: string; description: string | null; timestamp: string | null }[]
}
interface Allocation {
  allocation_id: string
  status: string
  part_number: string
  quantity: number
  source_id: string
  reserved_at: string | null
  confirmed_at: string | null
}

interface Operations {
  order: OrderRow & {
    customer_phone: string | null
    customer_company: string | null
    ship_to_address: string | null
    ship_to_city: string | null
    ship_to_country: string | null
    machine_context: string | null
    fulfilment_mode: string | null
    fulfilment_service_level: string | null
    fulfilment_transit_days: number | null
    fulfilment_eta: string | null
    fulfilment_cost: number | null
    fulfilment_currency: string | null
    integration_label: string
  }
  steps: Step[]
  next_action: { key: string; label: string } | null
  source: { id: string | null; name: string | null; city: string | null; country: string | null }
  allocation: Allocation | null
  fulfilment: { confirmed_at: string | null; external_order_id: string | null; synced_at: string | null; data_source: string | null }
  shipment: Shipment | null
  service_job: ServiceJob | null
  completed_at: string | null
  completed: boolean
  cancelled: boolean
  can_cancel: boolean
}

const STATUS_LABEL: Record<string, string> = {
  CREATED: 'Placed',
  ACCEPTED: 'In processing',
  FULFILLED: 'Delivered',
  CLOSED: 'Completed',
  CANCELLED: 'Cancelled',
}

/** Which lifecycle step each operations action belongs to. */
const ACTION_STEP: Record<string, StepKey> = {
  allocate: 'allocation',
  fulfil: 'fulfilment',
  create_shipment: 'shipment',
  dispatch: 'shipment',
  in_transit: 'tracking',
  deliver: 'tracking',
  create_service_job: 'service',
  receive: 'service',
  start: 'service',
  install: 'service',
  complete: 'service',
}

const STEP_INTRO: Record<StepKey, string> = {
  order: 'The order as placed by the customer.',
  allocation: 'Reserving stock for the order.',
  fulfilment: 'Confirming how and from where the order is fulfilled.',
  shipment: 'Creating and dispatching the shipment.',
  tracking: 'Following the shipment to the dealer.',
  service: 'Dealer receives the part and completes the service work.',
  completed: 'The finished order and its references.',
}

const fmtDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
const fmtDate = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleDateString('en-GB', { dateStyle: 'medium' }) : '—')
const words = (s: string | null | undefined) => (s ? s.replace(/_/g, ' ').toLowerCase() : '—')
const partsText = (parts: OrderRow['parts']) => parts.map((p) => `${p.part_name ?? p.part_number} × ${p.quantity}`).join(', ')

const ORDER_HASH = '#/orders'

function orderIdFromHash(): string | null {
  const m = window.location.hash.match(/^#\/orders\/([^/?]+)/)
  return m?.[1] ? decodeURIComponent(m[1]) : null
}

export function OrdersPage({ onHome }: { onHome: () => void }) {
  const [openId, setOpenId] = useState<string | null>(orderIdFromHash())

  useEffect(() => {
    const onHash = () => setOpenId(orderIdFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <main className="ps ord-screen" id="orders">
      <SiteHeader
        position="sticky"
        current="orders"
        onBrandClick={(event: MouseEvent<HTMLAnchorElement>) => {
          event.preventDefault()
          onHome()
        }}
      />
      <div className="ord">{openId ? <OrderDetail orderId={openId} /> : <OrderList />}</div>
    </main>
  )
}

/* ------------------------------------------------------------------------------------------------ list */

const PAGE_SIZE = 15
type SortKey = 'date_desc' | 'date_asc' | 'id_desc' | 'id_asc' | 'customer'

function StatusPill({ status }: { status: string }) {
  return <span className={`ord__status ord__status--${status.toLowerCase()}`}>{STATUS_LABEL[status] ?? status}</span>
}

function OrderList() {
  const [rows, setRows] = useState<OrderRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('ALL')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sort, setSort] = useState<SortKey>('date_desc')
  const [page, setPage] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/orders')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Orders could not be loaded (${r.status}).`))))
      .then((d) => !cancelled && setRows(d.orders))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [])

  const summary = useMemo(() => {
    const all = rows ?? []
    return {
      total: all.length,
      placed: all.filter((r) => r.status === 'CREATED').length,
      processing: all.filter((r) => r.status === 'ACCEPTED' || r.status === 'FULFILLED').length,
      completed: all.filter((r) => r.status === 'CLOSED').length,
    }
  }, [rows])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const fromT = from ? new Date(`${from}T00:00:00`).getTime() : null
    const toT = to ? new Date(`${to}T23:59:59.999`).getTime() : null
    const list = (rows ?? []).filter((r) => {
      if (status !== 'ALL' && r.status !== status) return false
      const t = new Date(r.placed_at).getTime()
      if (fromT != null && t < fromT) return false
      if (toT != null && t > toT) return false
      if (!q) return true
      return [r.order_id, r.customer_name, r.customer_email ?? '', r.dealer_name ?? '', ...r.parts.flatMap((p) => [p.part_number, p.part_name ?? ''])].some((x) =>
        x.toLowerCase().includes(q),
      )
    })
    const by: Record<SortKey, (a: OrderRow, b: OrderRow) => number> = {
      date_desc: (a, b) => b.placed_at.localeCompare(a.placed_at),
      date_asc: (a, b) => a.placed_at.localeCompare(b.placed_at),
      id_desc: (a, b) => b.order_id.localeCompare(a.order_id),
      id_asc: (a, b) => a.order_id.localeCompare(b.order_id),
      customer: (a, b) => a.customer_name.localeCompare(b.customer_name),
    }
    return [...list].sort(by[sort])
  }, [rows, query, status, from, to, sort])

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const current = Math.min(page, pages - 1)
  const shown = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
  const reset = <T,>(set: (v: T) => void) => (v: T) => { set(v); setPage(0) }

  return (
    <section>
      <header className="ord__head">
        <div>
          <p className="ord__eyebrow">HCME After-Sales · Operations</p>
          <h1>Orders</h1>
          <p className="ord__sub">Manage and process Parts Store orders</p>
        </div>
        <span className="ord__demo-tag">SYNTHETIC_DEMO · no live ERP, carrier or dealer system is connected</span>
      </header>

      <div className="ord__summary" aria-label="Order summary">
        <SummaryCard label="Total orders" value={summary.total} loaded={!!rows} />
        <SummaryCard label="Placed" value={summary.placed} loaded={!!rows} tone="orange" />
        <SummaryCard label="In processing" value={summary.processing} loaded={!!rows} tone="blue" />
        <SummaryCard label="Completed" value={summary.completed} loaded={!!rows} tone="green" />
      </div>

      {error && <p className="ord__error" role="alert">{error}</p>}
      {!rows && !error && <p className="ord__muted">Loading orders…</p>}
      {rows && rows.length === 0 && (
        <div className="ord__empty">No orders yet. Orders appear here as soon as a customer places one in the Parts Store.</div>
      )}

      {rows && rows.length > 0 && (
        <>
          <div className="ord__toolbar">
            <input
              type="search"
              className="ord__search"
              placeholder="Search by order ID, customer, part or dealer"
              aria-label="Search orders"
              value={query}
              onChange={(e) => reset(setQuery)(e.target.value)}
            />
            <select className="ord__select" aria-label="Filter by status" value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
              <option value="ALL">All statuses</option>
              {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className="ord__date">
              <span>From</span>
              <input type="date" value={from} max={to || undefined} onChange={(e) => reset(setFrom)(e.target.value)} aria-label="Ordered from" />
            </label>
            <label className="ord__date">
              <span>To</span>
              <input type="date" value={to} min={from || undefined} onChange={(e) => reset(setTo)(e.target.value)} aria-label="Ordered to" />
            </label>
            <select className="ord__select" aria-label="Sort orders" value={sort} onChange={(e) => reset(setSort)(e.target.value as SortKey)}>
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
              <option value="id_desc">Order ID ↓</option>
              <option value="id_asc">Order ID ↑</option>
              <option value="customer">Customer A–Z</option>
            </select>
            {(query || status !== 'ALL' || from || to) && (
              <button type="button" className="ord__clear" onClick={() => { setQuery(''); setStatus('ALL'); setFrom(''); setTo(''); setPage(0) }}>Clear filters</button>
            )}
            <span className="ord__count">{filtered.length} of {rows.length}</span>
          </div>

          <div className="ord__table-wrap">
            <table className="ord__table">
              <thead>
                <tr><th>Order ID</th><th>Customer</th><th>Parts</th><th>Dealer</th><th>Status</th><th>Order date</th><th className="ord__th-action">Action</th></tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.order_id} data-testid="order-row">
                    <td><a className="ord__id" href={`${ORDER_HASH}/${encodeURIComponent(r.order_id)}`}>{r.order_id}</a></td>
                    <td>
                      <div className="ord__cust">{r.customer_name}</div>
                      {r.customer_email && <div className="ord__cust-sub">{r.customer_email}</div>}
                    </td>
                    <td className="ord__parts">{partsText(r.parts)}</td>
                    <td>{r.dealer_name ?? '—'}</td>
                    <td><StatusPill status={r.status} /></td>
                    <td className="ord__nowrap">{fmtDate(r.placed_at)}</td>
                    <td className="ord__td-action">
                      <a className="ord__open" href={`${ORDER_HASH}/${encodeURIComponent(r.order_id)}`}>Open →</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && <p className="ord__muted ord__pad">No orders match these filters.</p>}
          </div>

          {pages > 1 && (
            <div className="ord__pager">
              <button type="button" className="ord__pbtn" disabled={current === 0} onClick={() => setPage(current - 1)}>← Previous</button>
              <span className="ord__muted">Page {current + 1} of {pages}</span>
              <button type="button" className="ord__pbtn" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next →</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function SummaryCard({ label, value, loaded, tone }: { label: string; value: number; loaded: boolean; tone?: 'orange' | 'blue' | 'green' }) {
  return (
    <div className={`ord__stat${tone ? ` ord__stat--${tone}` : ''}`} data-testid={`summary-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <span className="ord__stat-label">{label}</span>
      <strong className="ord__stat-value">{loaded ? value : '—'}</strong>
    </div>
  )
}

/* ------------------------------------------------------------------------------------------------ detail */

function OrderDetail({ orderId }: { orderId: string }) {
  const [ops, setOps] = useState<Operations | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<StepKey | null>(null)

  /** The step that needs attention: the first one whose persisted state is "current"; the last one once everything is done. */
  const focusStep = (o: Operations): StepKey => {
    if (o.cancelled) return 'order'
    const cur = o.steps.find((s) => s.state === 'current')
    return cur ? cur.key : 'completed'
  }

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/v1/orders/${encodeURIComponent(orderId)}/operations`)
      if (!r.ok) throw new Error(r.status === 404 ? `Order ${orderId} was not found.` : `The order could not be loaded (${r.status}).`)
      const d: Operations = await r.json()
      setOps(d)
      setSelected((prev) => prev ?? focusStep(d))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [orderId])

  useEffect(() => {
    load()
  }, [load])

  const run = async (action: string) => {
    setBusy(true)
    setError(null)
    try {
      const r = await fetch(`/api/v1/orders/${encodeURIComponent(orderId)}/ops/${action}`, { method: 'POST' })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error?.message || d.detail || 'That step could not be completed.')
      setOps(d as Operations)
      setSelected(focusStep(d as Operations)) // move on to the step that needs attention next
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      await load()
    } finally {
      setBusy(false)
    }
  }

  const back = (
    <a className="ord__back" href={ORDER_HASH} onClick={(e) => { e.preventDefault(); window.location.hash = ORDER_HASH }}>← All orders</a>
  )
  if (error && !ops) return <section>{back}<p className="ord__error" role="alert">{error}</p></section>
  if (!ops) return <section>{back}<p className="ord__muted">Loading order…</p></section>

  const o = ops.order
  const active: StepKey = selected ?? focusStep(ops)
  const activeStep = ops.steps.find((s) => s.key === active)!
  const nextStep = ops.next_action ? ACTION_STEP[ops.next_action.key] : undefined
  const actionHere = ops.next_action && nextStep === active ? ops.next_action : null
  const shipTo = [o.dealer_name, o.ship_to_address, [o.ship_to_city, o.ship_to_country].filter(Boolean).join(', ')].filter(Boolean).join(' · ')

  return (
    <section>
      {back}
      <header className="ord__detail-head">
        <div>
          <p className="ord__eyebrow">Order</p>
          <h1 data-testid="detail-order-id">{o.order_id}</h1>
          <p className="ord__sub">{o.customer_name}{o.customer_email ? ` · ${o.customer_email}` : ''} · placed {fmtDateTime(o.placed_at)}</p>
        </div>
        <div className="ord__detail-status">
          <StatusPill status={o.status} />
          <span className="ord__demo-tag">SYNTHETIC_DEMO</span>
        </div>
      </header>

      <div className="ord__layout">
        <aside className="ord__panel ord__info" aria-label="Customer and order information">
          <h2 className="ord__panel-title">Customer / order information</h2>
          <dl>
            <dt>Customer</dt><dd>{o.customer_name}</dd>
            <dt>Email</dt><dd>{o.customer_email ?? '—'}</dd>
            {o.customer_phone && (<><dt>Phone</dt><dd>{o.customer_phone}</dd></>)}
            {o.customer_company && (<><dt>Company</dt><dd>{o.customer_company}</dd></>)}
            <dt>Parts</dt><dd>{partsText(o.parts)}</dd>
            <dt>Part no.</dt><dd>{o.parts.map((p) => p.part_number).join(', ')}</dd>
            <dt>Dealer</dt><dd>{o.dealer_name ?? '—'}</dd>
            <dt>Deliver to</dt><dd>{shipTo || '—'}</dd>
          </dl>
        </aside>

        <div className="ord__panel ord__ops" aria-label="Business operations processing">
          <h2 className="ord__panel-title">Business operations processing</h2>

          <ol className="ord__steps" aria-label="Order lifecycle">
            {ops.steps.map((s, i) => (
              <li key={s.key} className={`ord__step ord__step--${s.state}${s.key === active ? ' is-selected' : ''}`} data-step={s.key} data-state={s.state}>
                <button
                  type="button"
                  className="ord__step-btn"
                  aria-current={s.key === active ? 'step' : undefined}
                  onClick={() => setSelected(s.key)}
                >
                  <span className="ord__step-dot">{s.state === 'done' ? '✓' : i + 1}</span>
                  <span className="ord__step-label">{s.key === 'order' ? 'Order placed' : s.label}</span>
                  <span className="ord__step-detail">{s.detail ? words(s.detail) : s.state === 'done' ? 'done' : s.state === 'current' ? 'in progress' : 'waiting'}</span>
                </button>
              </li>
            ))}
          </ol>

          {ops.cancelled ? (
            <p className="ord__cancelled">This order was cancelled. No further steps are possible.</p>
          ) : ops.completed ? (
            <p className="ord__done">✓ Lifecycle completed. The order is closed.</p>
          ) : ops.next_action && nextStep !== active ? (
            <p className="ord__next">
              Next step: <strong>{ops.next_action.label}</strong> —{' '}
              <button type="button" className="ord__link" onClick={() => setSelected(nextStep!)}>go to {ops.steps.find((s) => s.key === nextStep)?.label}</button>
            </p>
          ) : null}
          {error && <p className="ord__error" role="alert">{error}</p>}

          <div className="ord__step-panel" key={active} role="region" aria-live="polite" aria-label={`${activeStep.label} details`} data-panel={active}>
            <div className="ord__step-head">
              <div>
                <h3>{active === 'order' ? 'Order placed' : activeStep.label}</h3>
                <p className="ord__muted">{STEP_INTRO[active]}</p>
              </div>
              <span className={`ord__chip ord__chip--${activeStep.state}`}>{activeStep.state === 'done' ? 'Done' : activeStep.state === 'current' ? 'In progress' : 'Not started'}</span>
            </div>

            {activeStep.state === 'pending' && active !== 'order' && (
              <p className="ord__pending">This step has not started yet. It becomes available once the earlier steps are complete.</p>
            )}

            <StepBody step={active} ops={ops} />

            {actionHere && (
              <div className="ord__actionbar">
                <button type="button" className="ord__btn" disabled={busy} onClick={() => run(actionHere.key)} data-action={actionHere.key}>
                  {busy ? 'Working…' : `${actionHere.label} →`}
                </button>
                {ops.can_cancel && (
                  <button
                    type="button"
                    className="ord__btn ord__btn--ghost"
                    disabled={busy}
                    data-action="cancel"
                    onClick={() => { if (window.confirm(`Cancel order ${o.order_id}? This cannot be undone.`)) run('cancel') }}
                  >
                    Cancel order
                  </button>
                )}
              </div>
            )}
            {!actionHere && ops.can_cancel && !ops.cancelled && (
              <div className="ord__actionbar">
                <button
                  type="button"
                  className="ord__btn ord__btn--ghost"
                  disabled={busy}
                  data-action="cancel"
                  onClick={() => { if (window.confirm(`Cancel order ${o.order_id}? This cannot be undone.`)) run('cancel') }}
                >
                  Cancel order
                </button>
              </div>
            )}
          </div>
          <p className="ord__note">{o.integration_label}</p>
        </div>
      </div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (<><dt>{label}</dt><dd>{children}</dd></>)
}

function Depot({ ops }: { ops: Operations }) {
  const s = ops.source
  if (!s.id) return <>—</>
  const place = [s.name, [s.city, s.country].filter(Boolean).join(', ')].filter(Boolean).join(' · ')
  return <>{place || s.id.replace(/-/g, ' ').toLowerCase()} <span className="ord__muted">({s.id})</span></>
}

function StepBody({ step, ops }: { step: StepKey; ops: Operations }) {
  const o = ops.order
  const sh = ops.shipment
  const sj = ops.service_job
  const al = ops.allocation
  const freight = o.fulfilment_cost != null ? `€${Number(o.fulfilment_cost).toFixed(2)} ${o.fulfilment_currency ?? 'EUR'} (demo rate)` : '—'
  const shipTo = [o.dealer_name, o.ship_to_address, [o.ship_to_city, o.ship_to_country].filter(Boolean).join(', ')].filter(Boolean).join(' · ')
  const transport = [o.fulfilment_mode, o.fulfilment_service_level].filter(Boolean).map((x) => words(x as string)).join(' · ')

  if (step === 'order') {
    return (
      <dl className="ord__dl">
        <Field label="Order ID">{o.order_id}</Field>
        <Field label="Order date">{fmtDateTime(o.placed_at)}</Field>
        <Field label="Customer">{o.customer_name}{o.customer_email ? ` · ${o.customer_email}` : ''}{o.customer_phone ? ` · ${o.customer_phone}` : ''}</Field>
        <Field label="Parts & quantities">{partsText(o.parts)}</Field>
        <Field label="Dealer">{o.dealer_name ?? '—'}</Field>
        <Field label="Delivery address">{shipTo || '—'}</Field>
        <Field label="Order status"><StatusPill status={o.status} /></Field>
      </dl>
    )
  }
  if (step === 'allocation') {
    return (
      <dl className="ord__dl">
        <Field label="Allocation status">{al ? words(al.status) : 'not allocated yet'}</Field>
        <Field label="Part(s) allocated">{al ? `${o.parts[0]?.part_name ?? al.part_number} (${al.part_number}) × ${al.quantity}` : partsText(o.parts)}</Field>
        <Field label="Selected fulfilment">{transport || '—'}</Field>
        <Field label="Source / depot"><Depot ops={ops} /></Field>
        {al && <Field label="Allocation ID">{al.allocation_id}</Field>}
        {al && <Field label="Reserved">{fmtDateTime(al.reserved_at)}</Field>}
        {al && <Field label="Confirmed">{fmtDateTime(al.confirmed_at)}</Field>}
        <Field label="Stock data"><span className="ord__chip ord__chip--demo">SYNTHETIC_DEMO</span></Field>
      </dl>
    )
  }
  if (step === 'fulfilment') {
    return (
      <dl className="ord__dl">
        <Field label="Fulfilment option">{transport || '—'}</Field>
        <Field label="Source / depot"><Depot ops={ops} /></Field>
        <Field label="Transport method">{o.fulfilment_mode ? words(o.fulfilment_mode) : '—'}</Field>
        <Field label="Transit time">{o.fulfilment_transit_days != null ? `${o.fulfilment_transit_days} business day${o.fulfilment_transit_days === 1 ? '' : 's'}` : '—'}</Field>
        <Field label="Estimated delivery">{fmtDate(o.fulfilment_eta)}</Field>
        <Field label="Freight cost">{freight}</Field>
        <Field label="Fulfilment status">{ops.fulfilment.confirmed_at ? `confirmed ${fmtDateTime(ops.fulfilment.confirmed_at)}` : ops.steps.find((s) => s.key === 'fulfilment')?.state === 'current' ? 'awaiting confirmation' : 'not started'}</Field>
        {ops.fulfilment.confirmed_at && <Field label="Order system">{ops.fulfilment.data_source === 'SYNTHETIC_DEMO' ? 'simulated submission (no ERP connected)' : ops.fulfilment.data_source ?? '—'}</Field>}
        <Field label="Rates"><span className="ord__chip ord__chip--demo">SYNTHETIC_DEMO</span></Field>
      </dl>
    )
  }
  if (step === 'shipment') {
    return (
      <dl className="ord__dl">
        <Field label="Shipment status">{sh ? words(sh.status) : 'not created yet'}</Field>
        <Field label="Shipment ID">{sh?.shipment_id ?? '—'}</Field>
        <Field label="Selected transport">{transport || '—'}{sh?.carrier ? ` · ${sh.carrier}` : ''}</Field>
        <Field label="Service tier">{sh?.service_tier ? words(sh.service_tier) : '—'}</Field>
        <Field label="Origin → destination">{sh ? `${sh.origin ?? '—'} → ${sh.destination_dealer_name ?? sh.destination ?? '—'}` : '—'}</Field>
        <Field label="Dispatched">{sh?.shipped_at ? fmtDateTime(sh.shipped_at) : sh ? 'not dispatched yet' : '—'}</Field>
        <Field label="Carrier data"><span className="ord__chip ord__chip--demo">SYNTHETIC_DEMO</span></Field>
      </dl>
    )
  }
  if (step === 'tracking') {
    return (
      <>
        <dl className="ord__dl">
          <Field label="Tracking ID">{sh?.tracking_number ?? '—'}</Field>
          <Field label="Shipment status">{sh ? words(sh.status) : 'no shipment yet'}</Field>
          <Field label="Estimated delivery">{fmtDate(sh?.eta ?? o.fulfilment_eta)}</Field>
          {sh?.delivered_at && <Field label="Delivered">{fmtDateTime(sh.delivered_at)}</Field>}
        </dl>
        <h4 className="ord__sub-title">Tracking events</h4>
        {sh && sh.events.length > 0 ? (
          <ul className="ord__timeline">
            {sh.events.map((e) => (
              <li key={e.id}>
                <strong>{words(e.event_type)}</strong>
                <span>[SIMULATED] {e.description ?? ''}{e.location ? ` · ${e.location}` : ''}</span>
                <time>{fmtDateTime(e.timestamp)}</time>
              </li>
            ))}
          </ul>
        ) : (
          <p className="ord__muted">No tracking events yet. They appear once the shipment is dispatched.</p>
        )}
      </>
    )
  }
  if (step === 'service') {
    const milestones: [string, string | null | undefined][] = [
      ['Part received at dealer', sj?.received_at],
      ['Service work started', sj?.started_at],
      ['Installation recorded', sj?.installed_at],
      ['Service completed', sj?.completed_at],
    ]
    return (
      <>
        <dl className="ord__dl">
          <Field label="Dealer">{sj?.dealer_name ?? o.dealer_name ?? '—'}</Field>
          <Field label="Service job">{sj?.service_job_id ?? 'not created yet'}</Field>
          <Field label="Work order">{sj?.work_order_number ?? '—'}</Field>
          <Field label="Service status">{sj ? words(sj.status) : '—'}</Field>
          <Field label="Dealer system"><span className="ord__chip ord__chip--demo">SYNTHETIC_DEMO</span></Field>
        </dl>
        <h4 className="ord__sub-title">Service milestones</h4>
        <ul className="ord__milestones">
          {milestones.map(([label, ts]) => (
            <li key={label} className={ts ? 'is-done' : ''}>
              <span className="ord__ms-dot">{ts ? '✓' : ''}</span>
              <span>{label}</span>
              <time>{ts ? fmtDateTime(ts) : 'pending'}</time>
            </li>
          ))}
        </ul>
      </>
    )
  }
  // completed
  const summary: [string, string | null | undefined][] = [
    ['Order placed', o.placed_at],
    ['Allocation confirmed', al?.confirmed_at],
    ['Fulfilment confirmed', ops.fulfilment.confirmed_at],
    ['Shipment dispatched', sh?.shipped_at],
    ['Delivered to dealer', sh?.delivered_at],
    ['Service completed', sj?.completed_at],
  ]
  return (
    <>
      <dl className="ord__dl">
        <Field label="Final order status"><StatusPill status={o.status} /></Field>
        <Field label="Order ID">{o.order_id}</Field>
        <Field label="Shipment / tracking">{sh ? `${sh.shipment_id}${sh.tracking_number ? ` · ${sh.tracking_number}` : ''}` : '—'}</Field>
        <Field label="Service / work order">{sj ? `${sj.service_job_id}${sj.work_order_number ? ` · ${sj.work_order_number}` : ''}` : '—'}</Field>
        <Field label="Completed">{ops.completed_at ? fmtDateTime(ops.completed_at) : ops.completed ? '—' : 'not completed yet'}</Field>
      </dl>
      <h4 className="ord__sub-title">Lifecycle summary</h4>
      <ul className="ord__milestones">
        {summary.map(([label, ts]) => (
          <li key={label} className={ts ? 'is-done' : ''}>
            <span className="ord__ms-dot">{ts ? '✓' : ''}</span>
            <span>{label}</span>
            <time>{ts ? fmtDateTime(ts) : 'pending'}</time>
          </li>
        ))}
      </ul>
    </>
  )
}
