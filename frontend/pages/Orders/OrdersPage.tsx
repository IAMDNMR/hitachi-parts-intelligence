import { useCallback, useEffect, useState, type MouseEvent } from 'react'
import './OrdersPage.css'

import { SiteHeader } from '../../components/SiteHeader/SiteHeader'

/**
 * Orders — the business / operations area. Everything on this screen is read from, and written to, the existing Neo4j AuraDB through the FastAPI
 * backend: the list from GET /orders, the lifecycle from GET /orders/{id}/operations, every step from POST /orders/{id}/ops/{action}.
 * Nothing is kept in the browser (no localStorage / sessionStorage); a refresh shows exactly what is stored.
 */

interface OrderRow {
  order_id: string
  status: string
  customer_name: string
  dealer_name: string | null
  parts: { part_number: string; part_name: string | null; quantity: number }[]
  placed_at: string
}

interface Step { key: string; label: string; state: 'done' | 'current' | 'pending'; detail: string | null }

interface ShipmentEvent { id: string; event_type: string; description: string | null; location: string | null; timestamp: string | null }

interface Operations {
  order: OrderRow & {
    customer_email: string
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
  shipment: { shipment_id: string; status: string; tracking_number: string | null; carrier: string | null; events: ShipmentEvent[] } | null
  service_job_id: string | null
  service_job_status: string | null
  completed: boolean
  cancelled: boolean
  can_cancel: boolean
}

const STATUS_LABEL: Record<string, string> = {
  CREATED: 'Placed',
  ACCEPTED: 'In fulfilment',
  FULFILLED: 'Delivered',
  CLOSED: 'Completed',
  CANCELLED: 'Cancelled',
}

const fmt = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

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
      <div className="ord">
        {openId ? <OrderDetail orderId={openId} /> : <OrderList />}
      </div>
    </main>
  )
}

const PAGE_SIZE = 15

function OrderList() {
  const [rows, setRows] = useState<OrderRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('ALL')
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

  return (
    <section>
      <header className="ord__head">
        <h1>Orders</h1>
        <p>Every order placed in the Parts Store, read live from the database. Open an order to process it: allocation, fulfilment, shipment, tracking and dealer service.</p>
      </header>
      {error && <p className="ord__error" role="alert">{error}</p>}
      {!rows && !error && <p className="ord__muted">Loading orders…</p>}
      {rows && rows.length === 0 && <p className="ord__muted">No orders yet. Orders appear here as soon as a customer places one in the Parts Store.</p>}
      {rows && rows.length > 0 && (() => {
        const q = query.trim().toLowerCase()
        const filtered = rows.filter(
          (r) =>
            (status === 'ALL' || r.status === status) &&
            (!q ||
              [r.order_id, r.customer_name, r.dealer_name ?? '', ...r.parts.flatMap((p) => [p.part_number, p.part_name ?? ''])].some((t) =>
                t.toLowerCase().includes(q),
              )),
        )
        const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
        const current = Math.min(page, pages - 1)
        const shown = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
        return (
        <>
        <div className="ord__filters">
          <input
            type="search"
            className="ord__search"
            placeholder="Search by order ID, customer, part or dealer"
            aria-label="Search orders"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(0) }}
          />
          <select className="ord__select" aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(0) }}>
            <option value="ALL">All statuses</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <span className="ord__muted">{filtered.length} of {rows.length} orders</span>
        </div>
        <div className="ord__table-wrap">
          <table className="ord__table">
            <thead>
              <tr><th>Order ID</th><th>Customer</th><th>Parts</th><th>Dealer</th><th>Status</th><th>Date</th><th /></tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.order_id} data-testid="order-row">
                  <td><strong>{r.order_id}</strong></td>
                  <td>{r.customer_name}</td>
                  <td>{r.parts.map((p) => `${p.part_name ?? p.part_number} × ${p.quantity}`).join(', ')}</td>
                  <td>{r.dealer_name ?? '—'}</td>
                  <td><span className={`ord__status ord__status--${r.status.toLowerCase()}`}>{STATUS_LABEL[r.status] ?? r.status}</span></td>
                  <td>{fmt(r.placed_at)}</td>
                  <td>
                    <a className="ord__open" href={`${ORDER_HASH}/${encodeURIComponent(r.order_id)}`}>Open</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <p className="ord__muted">No orders match your search.</p>}
        {pages > 1 && (
          <div className="ord__pager">
            <button type="button" className="ord__pbtn" disabled={current === 0} onClick={() => setPage(current - 1)}>← Previous</button>
            <span className="ord__muted">Page {current + 1} of {pages}</span>
            <button type="button" className="ord__pbtn" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next →</button>
          </div>
        )}
        </>
        )
      })()}
    </section>
  )
}

function OrderDetail({ orderId }: { orderId: string }) {
  const [ops, setOps] = useState<Operations | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/v1/orders/${encodeURIComponent(orderId)}/operations`)
      if (!r.ok) throw new Error(r.status === 404 ? `Order ${orderId} was not found.` : `The order could not be loaded (${r.status}).`)
      setOps(await r.json())
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
      setOps(d)
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
  const shipTo = [o.dealer_name, o.ship_to_address, [o.ship_to_city, o.ship_to_country].filter(Boolean).join(', ')].filter(Boolean).join(' · ')
  return (
    <section>
      {back}
      <header className="ord__head ord__head--row">
        <div>
          <h1 data-testid="detail-order-id">{o.order_id}</h1>
          <p>{o.customer_name} · placed {fmt(o.placed_at)}</p>
        </div>
        <span className={`ord__status ord__status--${o.status.toLowerCase()}`}>{STATUS_LABEL[o.status] ?? o.status}</span>
      </header>

      <ol className="ord__steps" aria-label="Order lifecycle">
        {ops.steps.map((s, i) => (
          <li key={s.key} className={`ord__step ord__step--${s.state}`} data-step={s.key} data-state={s.state}>
            <span className="ord__step-dot">{s.state === 'done' ? '✓' : i + 1}</span>
            <span className="ord__step-label">{s.label}</span>
            {s.detail && <span className="ord__step-detail">{s.detail.replace(/_/g, ' ').toLowerCase()}</span>}
          </li>
        ))}
      </ol>

      <div className="ord__action">
        {ops.completed ? (
          <p className="ord__done">✓ Lifecycle completed. The order is closed.</p>
        ) : ops.cancelled ? (
          <p className="ord__cancelled">This order was cancelled. No further steps are possible.</p>
        ) : ops.next_action ? (
          <button type="button" className="ord__btn" disabled={busy} onClick={() => run(ops.next_action!.key)} data-action={ops.next_action.key}>
            {busy ? 'Working…' : `${ops.next_action.label} →`}
          </button>
        ) : null}
        {ops.can_cancel && !ops.cancelled && (
          <button
            type="button"
            className="ord__btn ord__btn--ghost"
            disabled={busy}
            onClick={() => { if (window.confirm(`Cancel order ${o.order_id}? This cannot be undone.`)) run('cancel') }}
            data-action="cancel"
          >
            Cancel order
          </button>
        )}
        {error && <p className="ord__error" role="alert">{error}</p>}
        <p className="ord__note">{o.integration_label}</p>
      </div>

      <div className="ord__cols">
        <div className="ord__card">
          <h3>Customer</h3>
          <dl>
            <dt>Name</dt><dd>{o.customer_name}</dd>
            <dt>Email</dt><dd>{o.customer_email}</dd>
            {o.customer_phone && (<><dt>Phone</dt><dd>{o.customer_phone}</dd></>)}
            {o.customer_company && (<><dt>Company</dt><dd>{o.customer_company}</dd></>)}
          </dl>
        </div>
        <div className="ord__card">
          <h3>Order</h3>
          <dl>
            <dt>Parts</dt><dd>{o.parts.map((p) => `${p.part_name ?? p.part_number} (${p.part_number}) × ${p.quantity}`).join(', ')}</dd>
            {o.machine_context && (<><dt>Machine</dt><dd>{o.machine_context}</dd></>)}
            <dt>Deliver to</dt><dd>{shipTo || '—'}</dd>
            <dt>Fulfilment</dt>
            <dd>
              {[o.fulfilment_mode, o.fulfilment_service_level].filter(Boolean).join(' ')}
              {o.fulfilment_transit_days != null ? ` · ${o.fulfilment_transit_days} business days` : ''}
              {o.fulfilment_cost != null ? ` · €${Number(o.fulfilment_cost).toFixed(2)} freight` : ''}
            </dd>
          </dl>
        </div>
        {ops.shipment && (
          <div className="ord__card">
            <h3>Shipment &amp; tracking</h3>
            <dl>
              <dt>Shipment</dt><dd>{ops.shipment.shipment_id} · {ops.shipment.status.replace(/_/g, ' ').toLowerCase()}</dd>
              {ops.shipment.tracking_number && (<><dt>Tracking</dt><dd>{ops.shipment.tracking_number}</dd></>)}
            </dl>
            <ul className="ord__events">
              {ops.shipment.events.map((e) => (
                <li key={e.id}><strong>{e.event_type.replace(/_/g, ' ').toLowerCase()}</strong> <span>[SIMULATED] {e.description}</span></li>
              ))}
            </ul>
          </div>
        )}
        {ops.service_job_id && (
          <div className="ord__card">
            <h3>Dealer service</h3>
            <dl>
              <dt>Service job</dt><dd>{ops.service_job_id}</dd>
              <dt>Status</dt><dd>{(ops.service_job_status ?? '').replace(/_/g, ' ').toLowerCase()}</dd>
            </dl>
          </div>
        )}
      </div>
    </section>
  )
}
