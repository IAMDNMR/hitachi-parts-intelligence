import { useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import { MACHINE_STATUS_LABELS, STAGE_LABELS } from '../types'
import type { Machine, MachineStatus } from '../types'
import { IconChevronDown, IconSearch } from './Icons'

/**
 * THE FLEET.
 *
 * The entry point to the whole after-sales experience, and the first screen in
 * this product that is about a machine rather than about a part.
 *
 * What a list of machines has to answer at a glance is which ones need
 * attention — so status, warranty and the count of open requirements are the
 * columns that carry weight, and the identity columns stay quiet. It is
 * deliberately not a fleet-management screen: no utilisation, no location, no
 * hours, because none of those exist and a column of dashes is worse than no
 * column.
 */
interface Props {
  onOpen: (machineId: string) => void
}

const STATUSES: MachineStatus[] = ['working', 'down', 'in_workshop']

/** A dropdown built from the values actually present, never a fixed menu. */
function Picker({
  label,
  value,
  options,
  onChange,
  open,
  setOpen,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
  open: boolean
  setOpen: (v: boolean) => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return undefined
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, setOpen])

  const chosen = options.find((o) => o.value === value)
  const active = value !== 'any'

  return (
    <div className="ord__picker" ref={ref}>
      <button
        type="button"
        className={`ord__tool-btn${active ? ' is-active' : ''}`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {active && chosen ? chosen.label : label}
        <IconChevronDown />
      </button>
      {open && (
        <div className="ord__picker-pop" role="listbox">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={o.value === value}
              className={o.value === value ? 'is-current' : undefined}
              onClick={() => {
                onChange(o.value)
                setOpen(false)
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function MachineList({ onOpen }: Props) {
  const [machines, setMachines] = useState<Machine[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [model, setModel] = useState('any')
  const [status, setStatus] = useState('any')
  const [dealer, setDealer] = useState('any')
  const [warranty, setWarranty] = useState('any')
  const [openPicker, setOpenPicker] = useState<string | null>(null)

  /* The unfiltered fleet, fetched once. The facets are built from it rather
     than from the current result, so narrowing to one dealer does not empty
     the dealer menu down to that one dealer. */
  const [fleet, setFleet] = useState<Machine[] | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listMachines()
      .then((list) => !cancelled && setFleet(list))
      .catch(() => {
        /* the filtered fetch below reports the failure; one error is enough */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    // Debounced: typing a serial should not be one request per keystroke.
    const t = setTimeout(() => {
      api
        .listMachines({
          search: search.trim() || undefined,
          model: model === 'any' ? undefined : model,
          status: status === 'any' ? undefined : status,
          dealer_id: dealer === 'any' ? undefined : dealer,
          warranty: warranty === 'any' ? undefined : (warranty as 'in' | 'out'),
        })
        .then((list) => !cancelled && setMachines(list))
        .catch((err: unknown) => {
          if (cancelled) return
          setError(err instanceof ApiError ? err.message : 'Could not load the fleet.')
        })
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [search, model, status, dealer, warranty])

  const all = useMemo(() => fleet ?? [], [fleet])
  const models = useMemo(
    () => [...new Set(all.map((m) => m.model))].sort(),
    [all],
  )
  const dealers = useMemo(() => {
    const seen = new Map<string, string>()
    all.forEach((m) => seen.set(m.dealer.id, m.dealer.name))
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [all])

  const narrowed =
    search.trim() !== '' ||
    model !== 'any' ||
    status !== 'any' ||
    dealer !== 'any' ||
    warranty !== 'any'

  const clearAll = () => {
    setSearch('')
    setModel('any')
    setStatus('any')
    setDealer('any')
    setWarranty('any')
  }

  if (error) return <p className="ord__error">{error}</p>

  const rows = machines
  const needAttention = all.filter((m) => m.status !== 'working').length

  return (
    <>
      <section className="ord__cat-controls" aria-label="Find a machine">
        <div className="ord__cat-search">
          <IconSearch />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by serial, model or customer..."
            aria-label="Search the fleet"
          />
        </div>

        <div className="ord__cat-facets">
          <Picker
            label="Model"
            value={model}
            onChange={setModel}
            open={openPicker === 'model'}
            setOpen={(v) => setOpenPicker(v ? 'model' : null)}
            options={[
              { value: 'any', label: 'All models' },
              ...models.map((m) => ({ value: m, label: m })),
            ]}
          />
          <Picker
            label="Status"
            value={status}
            onChange={setStatus}
            open={openPicker === 'status'}
            setOpen={(v) => setOpenPicker(v ? 'status' : null)}
            options={[
              { value: 'any', label: 'Any status' },
              ...STATUSES.map((s) => ({ value: s, label: MACHINE_STATUS_LABELS[s] })),
            ]}
          />
          <Picker
            label="Dealer"
            value={dealer}
            onChange={setDealer}
            open={openPicker === 'dealer'}
            setOpen={(v) => setOpenPicker(v ? 'dealer' : null)}
            options={[
              { value: 'any', label: 'All dealers' },
              ...dealers.map(([id, name]) => ({ value: id, label: name })),
            ]}
          />
          <Picker
            label="Warranty"
            value={warranty}
            onChange={setWarranty}
            open={openPicker === 'warranty'}
            setOpen={(v) => setOpenPicker(v ? 'warranty' : null)}
            options={[
              { value: 'any', label: 'Any warranty state' },
              { value: 'in', label: 'In warranty' },
              { value: 'out', label: 'Out of warranty' },
            ]}
          />
          {narrowed && (
            <button type="button" className="ord__cat-clear" onClick={clearAll}>
              Clear filters
            </button>
          )}
        </div>
      </section>

      {fleet === null || rows === null ? (
        <p className="ord__muted">Loading…</p>
      ) : (
        <>
          {/* Counted from the fleet in hand, never a stored total. Only two
              figures, because a machine list is not a dashboard. */}
          <div className="ord__cat-measure">
            <p className="ord__cat-summary">
              <span className="ord__cat-figure">{all.length}</span> machine
              {all.length === 1 ? '' : 's'}
              <span className="ord__cat-sep" aria-hidden>
                ·
              </span>
              <span className="ord__cat-figure">{needAttention}</span> not working
            </p>
            <p className="ord__cat-result" role="status">
              {rows.length === all.length
                ? `Showing all ${all.length}`
                : `${rows.length} of ${all.length} shown`}
            </p>
          </div>

          {rows.length === 0 ? (
            <div className="ord__empty">
              <p className="ord__empty-title">No machines</p>
              <p className="ord__empty-body">
                Nothing in the fleet matches that. Clearing the filters will bring the rest
                back.
              </p>
            </div>
          ) : (
            <div className="ord__card ord__card--table">
              <table className="ord__table ord__table--fleet">
                <thead>
                  <tr>
                    <th>Serial</th>
                    <th>Model</th>
                    <th>Customer</th>
                    <th>Dealer</th>
                    <th>Status</th>
                    <th>Warranty</th>
                    <th>Open parts</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((m) => (
                    <tr
                      key={m.id}
                      tabIndex={0}
                      aria-label={`Open ${m.serial_number}`}
                      onClick={() => onOpen(m.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          onOpen(m.id)
                        }
                      }}
                    >
                      <td className="ord__td-serial">{m.serial_number}</td>
                      <td className="ord__td-quiet">{m.model}</td>
                      <td>
                        <span className="ord__cell-main">{m.customer.name}</span>
                        <span className="ord__cell-sub">{m.customer.region}</span>
                      </td>
                      <td className="ord__td-quiet">{m.dealer.name}</td>
                      <td>
                        <span className={`ord__mstatus is-${m.status}`}>
                          <span className="ord__avail-dot" aria-hidden />
                          {MACHINE_STATUS_LABELS[m.status]}
                        </span>
                      </td>
                      <td>
                        <span className={`ord__warr is-${m.in_warranty ? 'in' : 'out'}`}>
                          {m.in_warranty ? 'In warranty' : 'Expired'}
                        </span>
                      </td>
                      <td className="ord__td-lead">
                        {m.open_requirements > 0 ? (
                          <span className="ord__openreq">{m.open_requirements}</span>
                        ) : (
                          <span className="ord__muted-cell">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  )
}

/* ===================================================================== 360 */

/**
 * MACHINE 360.
 *
 * What is going on with this machine — as much of it as Release 1 can
 * honestly say.
 *
 * There is no service history here, no alerts and no orders, because Service
 * Job, Machine Alert and Order do not exist. A panel headed "Service history"
 * over an empty list promises a capability rather than reporting one, and the
 * fastest way to make this screen untrustworthy would be to fill it with
 * headings that never have anything under them.
 *
 * What it does have is the three things the existing data genuinely supports:
 * what this machine has needed, what it is waiting on, and what fits it.
 */
export function Machine360({
  machineId,
  onBack,
  onOpenPart,
  onRaise,
  onBrowseFitting,
}: {
  machineId: string
  onBack: () => void
  onOpenPart: (partId: string) => void
  onRaise: (machineId: string, partId?: string) => void
  onBrowseFitting: (machineId: string) => void
}) {
  const [machine, setMachine] = useState<
    Awaited<ReturnType<typeof api.getMachine>> | null
  >(null)
  const [history, setHistory] = useState<
    Awaited<ReturnType<typeof api.getMachineRequirements>> | null
  >(null)
  const [fits, setFits] = useState<Awaited<ReturnType<typeof api.getMachineParts>> | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'history' | 'fits'>('history')

  useEffect(() => {
    let cancelled = false
    setMachine(null)
    Promise.all([
      api.getMachine(machineId),
      api.getMachineRequirements(machineId),
      api.getMachineParts(machineId),
    ])
      .then(([m, h, f]) => {
        if (cancelled) return
        setMachine(m)
        setHistory(h)
        setFits(f)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load that machine.')
      })
    return () => {
      cancelled = true
    }
  }, [machineId])

  if (error) return <p className="ord__error">{error}</p>
  if (!machine) return <p className="ord__muted">Loading…</p>

  const open = (history ?? []).filter((r) => r.stage !== 'received')
  const date = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })

  return (
    <div className="ord__record">
      <button type="button" className="ord__btn ord__btn--ghost ord__back" onClick={onBack}>
        ← Machines
      </button>

      <header className="ord__record-head ord__machine-head">
        <div className="ord__record-ident">
          <span className="ord__partno">{machine.serial_number}</span>
          <h2 className="ord__record-title">{machine.model}</h2>
          <p className="ord__record-desc">
            {machine.customer.name} · supported by {machine.dealer.name}
          </p>
          <div className="ord__chips">
            <span className={`ord__mstatus is-${machine.status}`}>
              <span className="ord__avail-dot" aria-hidden />
              {MACHINE_STATUS_LABELS[machine.status]}
            </span>
            <span className={`ord__warr is-${machine.in_warranty ? 'in' : 'out'}`}>
              {machine.in_warranty ? 'In warranty' : 'Warranty expired'}
              {machine.warranty_end && ` · ${date(machine.warranty_end)}`}
            </span>
            <span className="ord__chip">Commissioned {date(machine.commissioned_at)}</span>
          </div>
        </div>

        <button type="button" className="ord__btn" onClick={() => onRaise(machine.id)}>
          Raise requirement
        </button>
      </header>

      {/* Three figures, each of which is a link to the thing it counts. */}
      <div className="ord__mfacts">
        <div>
          <dt>Open requirements</dt>
          <dd>{open.length}</dd>
        </div>
        <div>
          <dt>Parts ever needed</dt>
          <dd>{(history ?? []).length}</dd>
        </div>
        <div>
          <dt>Parts that fit</dt>
          <dd>{machine.fitting_parts}</dd>
        </div>
      </div>

      <nav className="ord__tabs" aria-label="Machine sections">
        <button
          type="button"
          className={`ord__tab${tab === 'history' ? ' is-current' : ''}`}
          aria-current={tab === 'history' ? 'true' : undefined}
          onClick={() => setTab('history')}
        >
          Parts needed ({(history ?? []).length})
        </button>
        <button
          type="button"
          className={`ord__tab${tab === 'fits' ? ' is-current' : ''}`}
          aria-current={tab === 'fits' ? 'true' : undefined}
          onClick={() => setTab('fits')}
        >
          Parts that fit ({machine.fitting_parts})
        </button>
      </nav>

      {tab === 'history' &&
        ((history ?? []).length === 0 ? (
          <p className="ord__muted">
            No parts have been required for this machine yet.
          </p>
        ) : (
          <div className="ord__card ord__card--table">
            <table className="ord__table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Part</th>
                  <th>Part number</th>
                  <th>Qty</th>
                  <th>Stage</th>
                  <th>Raised</th>
                </tr>
              </thead>
              <tbody>
                {(history ?? []).map((r) => (
                  <tr key={r.id} className="is-static">
                    <td className="ord__td-quiet">
                      {String(r.id).padStart(4, '0')}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ord__link"
                        onClick={() => onOpenPart(r.part.id)}
                      >
                        {r.part.name}
                      </button>
                      <span className="ord__cell-sub">{r.reason}</span>
                    </td>
                    <td className="ord__td-partno">{r.part.part_number}</td>
                    <td className="ord__td-lead">{r.quantity}</td>
                    <td>
                      <span className={`ord__stage-pill is-${r.stage}`}>
                        {STAGE_LABELS[r.stage]}
                      </span>
                    </td>
                    <td className="ord__td-quiet">{date(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {tab === 'fits' && (
        <>
          <p className="ord__note">
            Only these parts can be raised against a {machine.model}. The catalogue lists
            them against this model; anything else is refused rather than substituted.
            <button
              type="button"
              className="ord__link"
              style={{ marginLeft: 10 }}
              onClick={() => onBrowseFitting(machine.id)}
            >
              Open the catalogue filtered to this machine
            </button>
          </p>
          <div className="ord__card ord__card--table">
            <table className="ord__table">
              <thead>
                <tr>
                  <th>Part number</th>
                  <th>Part</th>
                  <th>Where it sits</th>
                  <th>Lead time</th>
                  <th>On hand</th>
                  <th className="ord__th-actions">Action</th>
                </tr>
              </thead>
              <tbody>
                {(fits ?? []).map((p) => (
                  <tr key={p.id} className="is-static">
                    <td className="ord__td-partno">{p.part_number}</td>
                    <td>
                      <button
                        type="button"
                        className="ord__link"
                        onClick={() => onOpenPart(p.id)}
                      >
                        {p.name}
                      </button>
                    </td>
                    <td className="ord__td-quiet">{p.assembly}</td>
                    <td className="ord__td-lead">
                      {p.lead_time_days} <span className="ord__unit">days</span>
                    </td>
                    <td className="ord__td-stock">
                      {p.stock ? (
                        <span
                          className={`ord__stock is-${
                            p.stock.qty_on_hand <= 0
                              ? 'out'
                              : p.stock.qty_on_hand <= p.stock.reorder_point
                                ? 'limited'
                                : 'in'
                          }`}
                        >
                          <span className="ord__stock-qty">{p.stock.qty_on_hand}</span>
                          <span className="ord__stock-where">{p.stock.warehouse}</span>
                        </span>
                      ) : (
                        <span className="ord__muted-cell">Not stocked</span>
                      )}
                    </td>
                    <td className="ord__row-actions">
                      <button
                        type="button"
                        className="ord__tool-btn"
                        onClick={() => onRaise(machine.id, p.id)}
                      >
                        Raise
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
