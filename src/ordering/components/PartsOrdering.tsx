import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import '../styles/ordering.css'

import { api, ApiError } from '../api'
import { STAGE_LABELS, STAGE_SEQUENCE } from '../types'
import type { RequirementDetail as Detail, Requirement, Stage } from '../types'
import {
  IconCheckCircle,
  IconChart,
  IconChevronDown,
  IconChevronRight,
  IconDoc,
  IconFilter,
  IconHome,
  IconHourglass,
  IconList,
  IconParts,
  IconWrench,
  IconPlus,
  IconSearch,
  IconTruck,
} from './Icons'
import { NewRequirementForm } from './NewRequirementForm'
import { PartRecord } from './PartRecord'
import { PartsCatalogue } from './PartsCatalogue'
import { PartsInsights } from './PartsInsights'
import { RequirementDetail } from './RequirementDetail'
import { RequirementsTable } from './RequirementsTable'
import { ServiceKits } from './ServiceKits'

/**
 * PARTS ORDERING.
 *
 * The Parts branch of The Ground, as something you can actually run rather
 * than only read: raise a requirement, check availability, order, allocate,
 * ship, receive. Backed by the FastAPI service in backend/parts_ordering —
 * state lives in a database on a server, not in this tab, so two people
 * looking at the same requirement see the same thing and a refresh loses
 * nothing.
 *
 * SHELL, NOT A PAGE
 * -----------------
 * This is laid out as an application: a fixed rail on the left saying where
 * you are and what else there is, a working area on the right. It was a
 * single centred column with two toggle buttons over a bare table, which
 * read as an admin screen nobody had finished — flat, no hierarchy, and no
 * way to tell at a glance whether anything needed attention. The rail is
 * charcoal because the palette already owns that colour (the milestone
 * nodes on The Ground are the same), and because a working tool should not
 * look like another page of the brochure it is reached from.
 *
 * There is no router here, matching the rest of the project (see App.jsx):
 * one hash route reaches this page, and which view it shows is local state,
 * because none of them is a destination anyone would link to directly.
 */
interface Props {
  onHome: () => void
  onOpenGround: () => void
}

type View =
  | { kind: 'list' }
  | { kind: 'new'; partId?: string }
  | { kind: 'edit'; id: number }
  | { kind: 'detail'; id: number }
  | { kind: 'catalogue' }
  | { kind: 'part'; partId: string }
  | { kind: 'insights' }
  | { kind: 'kits' }

const SECTION_OF: Record<View['kind'], 'requirements' | 'parts' | 'kits'> = {
  list: 'requirements',
  new: 'requirements',
  edit: 'requirements',
  detail: 'requirements',
  catalogue: 'parts',
  part: 'parts',
  insights: 'requirements',
  kits: 'kits',
}

export function PartsOrdering({ onHome, onOpenGround }: Props) {
  const [view, setView] = useState<View>({ kind: 'list' })
  const section = SECTION_OF[view.kind]
  const [requirements, setRequirements] = useState<Requirement[] | null>(null)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'open' | 'backorder' | 'received'>('all')
  const [query, setQuery] = useState('')
  const [stageFilter, setStageFilter] = useState<Stage | 'any'>('any')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const filterMenu = useRef<HTMLDivElement>(null)

  const loadList = useCallback(async () => {
    setError(null)
    try {
      setRequirements(await api.listRequirements())
    } catch (err) {
      setRequirements([])
      setError(err instanceof ApiError ? err.message : 'Could not load requirements.')
    }
  }, [])

  useEffect(() => {
    if (view.kind === 'list') void loadList()
  }, [view, loadList])

  // A popover that can only be shut by choosing from it is a trap — same
  // rule the row menu in RequirementsTable follows.
  useEffect(() => {
    if (!filtersOpen) return undefined
    const onDown = (e: MouseEvent) => {
      if (filterMenu.current && !filterMenu.current.contains(e.target as Node))
        setFiltersOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setFiltersOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [filtersOpen])

  useEffect(() => {
    if (view.kind !== 'detail') return
    let cancelled = false
    setError(null)
    api
      .getRequirement(view.id)
      .then((d) => !cancelled && setDetail(d))
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load that requirement.')
      })
    return () => {
      cancelled = true
    }
  }, [view])

  /**
   * What needs attention, counted from what is already loaded.
   *
   * Deliberately not four more API calls: the list is in hand, and a number
   * derived from it cannot disagree with the rows underneath it.
   */
  const stats = useMemo(() => {
    const list = requirements ?? []
    return {
      open: list.filter((r) => r.stage !== 'received').length,
      backorder: list.filter((r) => r.available_at_check === false && r.stage !== 'received')
        .length,
      inTransit: list.filter((r) => r.stage === 'shipped').length,
      closed: list.filter((r) => r.stage === 'received').length,
    }
  }, [requirements])

  /**
   * The chip counts, and the rows the chips + search + stage filter leave.
   *
   * The counts are of the whole list, not of what is currently on screen:
   * a chip that reported the size of its own result would read "Open (0)"
   * the moment a search hid the open ones, which is the opposite of what
   * the number is for.
   */
  const counts = useMemo(() => {
    const list = requirements ?? []
    return {
      all: list.length,
      open: list.filter((r) => r.stage !== 'received').length,
      backorder: list.filter((r) => r.available_at_check === false && r.stage !== 'received')
        .length,
      received: list.filter((r) => r.stage === 'received').length,
    }
  }, [requirements])

  const shown = useMemo(() => {
    let list = requirements ?? []
    if (filter === 'open') list = list.filter((r) => r.stage !== 'received')
    if (filter === 'backorder')
      list = list.filter((r) => r.available_at_check === false && r.stage !== 'received')
    if (filter === 'received') list = list.filter((r) => r.stage === 'received')
    if (stageFilter !== 'any') list = list.filter((r) => r.stage === stageFilter)
    const q = query.trim().toLowerCase()
    if (q)
      list = list.filter(
        (r) =>
          r.part.name.toLowerCase().includes(q) ||
          r.part.part_number.toLowerCase().includes(q) ||
          r.machine_serial.toLowerCase().includes(q),
      )
    return list
  }, [requirements, filter, stageFilter, query])

  const narrowed = filter !== 'all' || stageFilter !== 'any' || query.trim() !== ''

  const cancel = useCallback(
    async (r: Requirement) => {
      // A destructive action that cannot be undone asks first, and says what
      // will happen to the stock — which is the part people get wrong.
      const back =
        r.stage === 'inventory_allocated' || r.stage === 'shipped'
          ? ` The ${r.quantity} allocated will go back on the shelf.`
          : ''
      if (!window.confirm(`Cancel requirement #${r.id} for ${r.part.name}?${back}`)) return
      try {
        await api.cancelRequirement(r.id)
        await loadList()
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Could not cancel that requirement.')
      }
    },
    [loadList],
  )

  const home = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      onHome()
    },
    [onHome],
  )

  const ground = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      onOpenGround()
    },
    [onOpenGround],
  )

  /**
   * What the page calls itself.
   *
   * Keyed on the VIEW, not on the section it belongs to. Keyed on the
   * section, opening a part showed the heading "Parts catalogue" and the
   * catalogue's own strapline above a single part record — the page claiming
   * to be the list the reader had just left.
   *
   * A view that is about one record does not know its name until the record
   * has loaded, so the trail carries a placeholder the child replaces; see
   * `recordName` below.
   */
  const PAGE: Record<View['kind'], { crumb: string; title: string; strap: string }> = {
    list: {
      crumb: 'Requirements',
      title: 'Requirements',
      strap: 'Requirement to goods receipt, one step at a time.',
    },
    new: {
      crumb: 'New requirement',
      title: 'New requirement',
      strap: 'A part is needed for a machine. This is where that is written down.',
    },
    edit: {
      crumb: 'Edit requirement',
      title: 'Edit requirement',
      strap: 'Amend what was asked for, while it is still only a statement of intent.',
    },
    detail: {
      crumb: 'Requirement',
      title: 'Requirement',
      strap: 'Where this one stands, how it got there, and what happens next.',
    },
    catalogue: {
      crumb: 'Catalogue',
      title: 'Parts catalogue',
      strap:
        'Every part in the after-sales operation — identification, fitment, availability and usage.',
    },
    part: {
      crumb: 'Part record',
      title: 'Part record',
      strap: 'What it fits, what it supersedes, how long it takes to get, and who has needed one.',
    },
    kits: {
      crumb: 'Service kits',
      title: 'Service kits',
      strap:
        'A service as one orderable thing — the parts a job consumes, raised together and ahead of the failure.',
    },
    insights: {
      crumb: 'Insights',
      title: 'Parts insights',
      strap: 'Demand, lead times and supply status, read off the records already held.',
    },
  }
  const page = PAGE[view.kind]
  const { crumb, strap } = page
  const title = page.title

  /** The head of the section this view sits in — the step back up the trail. */
  const sectionRoot: { crumb: string; view: View } =
    section === 'parts'
      ? { crumb: PAGE.catalogue.crumb, view: { kind: 'catalogue' } }
      : section === 'kits'
        ? { crumb: PAGE.kits.crumb, view: { kind: 'kits' } }
        : { crumb: PAGE.list.crumb, view: { kind: 'list' } }

  return (
    <div className="ord">
      <aside className="ord__rail">
        <a className="ord__rail-brand" href="#" onClick={home}>
          <span className="ord__rail-brand-main">HITACHI</span>
          <span className="ord__rail-brand-sub">Parts</span>
        </a>

        <nav className="ord__rail-nav" aria-label="Sections">
          <button
            type="button"
            className={`ord__rail-link${section === 'requirements' ? ' is-current' : ''}`}
            aria-current={section === 'requirements' ? 'page' : undefined}
            onClick={() => setView({ kind: 'list' })}
          >
            <span className="ord__rail-label">
              <IconList />
              Requirements
            </span>
            {requirements && stats.open > 0 && (
              <span className="ord__rail-count">{stats.open}</span>
            )}
          </button>
          {/* Planned work sits beside reactive work, not inside it — a kit is
              raised because a service is due, not because something failed. */}
          <button
            type="button"
            className={`ord__rail-link${section === 'kits' ? ' is-current' : ''}`}
            aria-current={section === 'kits' ? 'page' : undefined}
            onClick={() => setView({ kind: 'kits' })}
          >
            <span className="ord__rail-label">
              <IconWrench />
              Service kits
            </span>
          </button>
          <button
            type="button"
            className={`ord__rail-link${section === 'parts' ? ' is-current' : ''}`}
            aria-current={section === 'parts' ? 'page' : undefined}
            onClick={() => setView({ kind: 'catalogue' })}
          >
            <span className="ord__rail-label">
              <IconParts />
              Parts catalogue
            </span>
          </button>
        </nav>

        <div className="ord__rail-foot">
          <a className="ord__rail-foot-lead" href="#/the-ground" onClick={ground}>
            The Ground
          </a>
          <a href="#" onClick={home}>
            <IconHome />
            Home
          </a>
        </div>
      </aside>

      <main className="ord__main">
        {/* Home / Parts / <section> / <where you are>.
            The section step is only drawn when it is not itself the page —
            a trail whose last two steps read "Catalogue / Catalogue" tells
            the reader nothing and costs a line. */}
        <nav className="ord__crumbs" aria-label="Breadcrumb">
          <a href="#" onClick={home} aria-label="Home">
            <IconHome />
          </a>
          <span aria-hidden>/</span>
          <button
            type="button"
            onClick={() =>
              setView({
                kind:
                  section === 'parts' ? 'catalogue' : section === 'kits' ? 'kits' : 'list',
              })
            }
          >
            Parts
          </button>
          <span aria-hidden>/</span>
          {crumb !== sectionRoot.crumb && (
            <>
              <button type="button" onClick={() => setView(sectionRoot.view)}>
                {sectionRoot.crumb}
              </button>
              <span aria-hidden>/</span>
            </>
          )}
          <span className="is-current" aria-current="page">
            {crumb}
          </span>
        </nav>

        <header className="ord__head">
          <div className="ord__head-text">
            <h1 className="ord__title">{title}</h1>
            <p className="ord__strap">{strap}</p>
          </div>

          {section === 'requirements' && view.kind === 'list' && (
            <button type="button" className="ord__btn" onClick={() => setView({ kind: 'new' })}>
              <IconPlus />
              New Requirement
            </button>
          )}
        </header>

        {section === 'requirements' && view.kind === 'list' && requirements && (
          <div className="ord__stats">
            <Stat
              label="Open"
              note="Awaiting processing"
              value={stats.open}
              icon={<IconDoc />}
              current={filter === 'open'}
              onSelect={() => setFilter(filter === 'open' ? 'all' : 'open')}
            />
            <Stat
              label="On Backorder"
              note="Supplier confirmation pending"
              value={stats.backorder}
              icon={<IconHourglass />}
              tone="warn"
              current={filter === 'backorder'}
              onSelect={() => setFilter(filter === 'backorder' ? 'all' : 'backorder')}
            />
            <Stat
              label="In Transit"
              note="On the way to site"
              value={stats.inTransit}
              icon={<IconTruck />}
              current={stageFilter === 'shipped'}
              onSelect={() => {
                setFilter('all')
                setStageFilter((v) => (v === 'shipped' ? 'any' : 'shipped'))
              }}
            />
            <Stat
              label="Received"
              note="Goods received"
              value={stats.closed}
              icon={<IconCheckCircle />}
              tone="ok"
              current={filter === 'received'}
              onSelect={() => setFilter(filter === 'received' ? 'all' : 'received')}
            />
          </div>
        )}

        {error && <p className="ord__error">{error}</p>}

        {view.kind === 'catalogue' && (
          <PartsCatalogue
            onOpen={(partId) => setView({ kind: 'part', partId })}
            onRaise={(partId) => setView({ kind: 'new', partId })}
          />
        )}

        {view.kind === 'part' && (
          <PartRecord
            key={view.partId}
            partId={view.partId}
            onBack={() => setView({ kind: 'catalogue' })}
            onRaise={(partId) => setView({ kind: 'new', partId })}
            onOpenPart={(partId) => setView({ kind: 'part', partId })}
          />
        )}

        {view.kind === 'edit' && (
          <EditRequirementForm
            id={view.id}
            onDone={() => setView({ kind: 'list' })}
            onCancel={() => setView({ kind: 'list' })}
          />
        )}

        {view.kind === 'new' && (
          <NewRequirementForm
            initialPartId={view.partId}
            onCancel={() => setView({ kind: 'list' })}
            onCreated={(req) => {
              setDetail(req)
              setView({ kind: 'detail', id: req.id })
            }}
          />
        )}

        {view.kind === 'detail' && detail && detail.id === view.id && (
          <RequirementDetail
            requirement={detail}
            onChanged={setDetail}
            onBack={() => setView({ kind: 'list' })}
          />
        )}

        {view.kind === 'list' && requirements && requirements.length > 0 && (
          <div className="ord__toolbar">
            <div className="ord__filters">
              {(['all', 'open', 'backorder', 'received'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  className={`ord__filter${filter === f ? ' is-current' : ''}`}
                  aria-pressed={filter === f}
                  onClick={() => setFilter(f)}
                >
                  {f === 'all'
                    ? 'All'
                    : f === 'open'
                      ? 'Open'
                      : f === 'backorder'
                        ? 'On backorder'
                        : 'Received'}
                  <span className="ord__filter-count">({counts[f]})</span>
                </button>
              ))}
            </div>

            <div className="ord__tools">
              <div className="ord__searchbox">
                <IconSearch />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by part name, number or machine..."
                  aria-label="Search requirements"
                />
              </div>

              <div className="ord__filter-menu" ref={filterMenu}>
                <button
                  type="button"
                  className={`ord__tool-btn${stageFilter !== 'any' ? ' is-active' : ''}`}
                  aria-expanded={filtersOpen}
                  onClick={() => setFiltersOpen((v) => !v)}
                >
                  <IconFilter />
                  Filters
                  <IconChevronDown />
                </button>
                {filtersOpen && (
                  <div className="ord__filter-pop">
                    <label className="ord__field">
                      <span>Stage</span>
                      <select
                        value={stageFilter}
                        onChange={(e) => setStageFilter(e.target.value as Stage | 'any')}
                      >
                        <option value="any">Any stage</option>
                        {STAGE_SEQUENCE.map((st) => (
                          <option key={st} value={st}>
                            {STAGE_LABELS[st]}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="button"
                      className="ord__btn ord__btn--ghost"
                      onClick={() => {
                        setStageFilter('any')
                        setQuery('')
                        setFilter('all')
                        setFiltersOpen(false)
                      }}
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {view.kind === 'kits' && (
          <ServiceKits
            onRaised={(machineSerial, count) => {
              /* Straight to the requirements they just created, filtered to
                 the machine — a kit that raises five lines and leaves the
                 reader on the kit screen has not told them it worked. */
              setQuery(machineSerial)
              setFilter('all')
              setStageFilter('any')
              setView({ kind: 'list' })
              setError(null)
              void count
            }}
          />
        )}

        {view.kind === 'insights' && <PartsInsights onBack={() => setView({ kind: 'list' })} />}

        {view.kind === 'list' && (
          <RequirementsTable
            requirements={requirements === null ? null : shown}
            filtered={narrowed}
            onOpen={(id) => setView({ kind: 'detail', id })}
            onEdit={(id) => setView({ kind: 'edit', id })}
            onCancel={cancel}
          />
        )}

        {view.kind === 'list' && requirements && requirements.length > 0 && (
          <section className="ord__insights-cta">
            <span className="ord__insights-cta-icon">
              <IconChart />
            </span>
            <div>
              <p className="ord__insights-cta-title">Parts insights</p>
              <p className="ord__insights-cta-body">
                Track demand, lead times and supply status across your fleet.
              </p>
            </div>
            <button
              type="button"
              className="ord__tool-btn"
              onClick={() => setView({ kind: 'insights' })}
            >
              <IconChart />
              View analytics
              <IconChevronRight />
            </button>
          </section>
        )}
      </main>
    </div>
  )
}

/**
 * One number, and the way to the rows behind it.
 *
 * A card is a button because the question a count provokes is "which ones" —
 * reading "1 on backorder" and then hunting for it in the table below is a
 * step the card can simply take for you.
 */
function Stat({
  label,
  note,
  value,
  icon,
  tone,
  current,
  onSelect,
}: {
  label: string
  note: string
  value: number
  icon: React.ReactNode
  tone?: 'ok' | 'warn'
  current: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={`ord__stat${tone ? ` is-${tone}` : ''}${current ? ' is-current' : ''}`}
      aria-pressed={current}
      onClick={onSelect}
    >
      <span className="ord__stat-icon">{icon}</span>
      <span className="ord__stat-body">
        <span className="ord__stat-value">{value}</span>
        <span className="ord__stat-label">{label}</span>
        <span className="ord__stat-note">{note}</span>
      </span>
      <span className="ord__stat-go" aria-hidden>
        <IconChevronRight />
      </span>
    </button>
  )
}

/**
 * Editing an existing requirement.
 *
 * Loads the record first rather than trusting the row that was clicked: the
 * list may have been on screen a while, and what can legally be changed
 * depends on the stage it is at NOW, not when the page was drawn.
 */
function EditRequirementForm({
  id,
  onDone,
  onCancel,
}: {
  id: number
  onDone: () => void
  onCancel: () => void
}) {
  const [req, setReq] = useState<Detail | null>(null)
  const [machineSerial, setMachineSerial] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .getRequirement(id)
      .then((d) => {
        if (cancelled) return
        setReq(d)
        setMachineSerial(d.machine_serial)
        setQuantity(d.quantity)
        setReason(d.reason)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load that requirement.')
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (error) return <p className="ord__error">{error}</p>
  if (!req) return <p className="ord__muted">Loading…</p>

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.updateRequirement(id, {
        machine_serial: machineSerial.trim(),
        quantity,
        reason: reason.trim(),
      })
      onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save those changes.')
    } finally {
      setBusy(false)
    }
  }

  const quantityChanged = quantity !== req.quantity

  return (
    <form className="ord__form" onSubmit={submit}>
      <h2 className="ord__form-title">
        Edit #{req.id} · {req.part.name}
      </h2>

      <label className="ord__field">
        <span>Machine serial</span>
        <input
          type="text"
          value={machineSerial}
          onChange={(e) => setMachineSerial(e.target.value)}
          maxLength={64}
          required
        />
      </label>

      <label className="ord__field">
        <span>Quantity</span>
        <input
          type="number"
          min={1}
          max={999}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
          required
        />
      </label>

      {quantityChanged && req.stage !== 'identified' && (
        <p className="ord__note">
          Changing the quantity sends this back to have its availability re-checked — the
          previous answer was about {req.quantity}, not {quantity}.
        </p>
      )}

      <label className="ord__field">
        <span>Reason</span>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={500}
          rows={3}
          required
        />
      </label>

      {error && <p className="ord__error">{error}</p>}

      <div className="ord__form-actions">
        <button type="button" className="ord__btn ord__btn--ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="ord__btn" disabled={busy}>
          {busy ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </form>
  )
}
