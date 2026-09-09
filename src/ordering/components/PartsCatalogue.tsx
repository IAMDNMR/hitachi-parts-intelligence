import { useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import type { MachineDetail, PartRow } from '../types'
import { thumbnailFor } from '../thumbnails'
import {
  IconCart,
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconCopy,
  IconDots,
  IconEye,
  IconSearch,
} from './Icons'

const PAGE_SIZE = 8

interface Props {
  /** When set, the catalogue is standing on a machine: it shows only the
   *  parts that fit it, and says so. */
  machineId?: string
  onClearMachine: () => void
  onOpen: (partId: string) => void
  /** Undefined raises a blank requirement; a part id pre-picks that part. */
  onRaise: (partId?: string) => void
}

type Availability = 'in' | 'limited' | 'out'
type SortKey = 'part_number' | 'name' | 'category' | 'availability' | 'lead_time' | 'stock'

const AVAILABILITY_LABEL: Record<Availability, string> = {
  in: 'In stock',
  limited: 'Limited',
  out: 'Out of stock',
}

/**
 * Can this part be had, in the only terms a catalogue reader cares about.
 *
 * Read off the shelf and its reorder point rather than a flag someone has
 * to remember to set: a part at or below the point it should be reordered
 * at cannot cover another requirement of any size without being replenished
 * first, which is "limited" in every sense that matters. A part with no
 * stock record at all is out — not unknown — because nothing on a shelf
 * somewhere that nobody counts can be promised to a machine.
 */
function availabilityOf(part: PartRow): Availability {
  if (!part.stock || part.stock.qty_on_hand <= 0) return 'out'
  if (part.stock.qty_on_hand <= part.stock.reorder_point) return 'limited'
  return 'in'
}

const AVAILABILITY_ORDER: Record<Availability, number> = { in: 0, limited: 1, out: 2 }

/** What is actually on the shelf. Null where the part has no stock record at
 *  all, which is a different answer from zero and is shown as one. */
function onHand(part: PartRow): number | null {
  return part.stock ? part.stock.qty_on_hand : null
}

/** The dozen-odd rows a page of numbered pagination should offer: the ends,
 *  the current neighbourhood, and an ellipsis for everything skipped. */
function pageList(pages: number, current: number): (number | '…')[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i)
  const out: (number | '…')[] = [0]
  const from = Math.max(1, current - 1)
  const to = Math.min(pages - 2, current + 1)
  if (from > 1) out.push('…')
  for (let i = from; i <= to; i += 1) out.push(i)
  if (to < pages - 2) out.push('…')
  out.push(pages - 1)
  return out
}

/**
 * A dropdown that filters the table.
 *
 * Closed it reads as its own label, open it is the list of values actually
 * present in the data — never a fixed menu, so it cannot offer a category
 * that no part is in.
 */
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

/** The actions a row offers beyond opening it: raising a requirement for the
 *  part, and taking its number away to quote somewhere else. */
function RowMenu({ part, onOpen, onRaise }: { part: PartRow; onOpen: () => void; onRaise: () => void }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
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
  }, [open])

  return (
    <div className="ord__menu" ref={ref}>
      <button
        type="button"
        className="ord__icon-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`More actions for ${part.name}`}
        onClick={() => setOpen((v) => !v)}
      >
        <IconDots />
      </button>
      {open && (
        <div className="ord__menu-pop" role="menu">
          <button type="button" role="menuitem" onClick={() => { setOpen(false); onOpen() }}>
            <IconEye />
            View record
          </button>
          <button type="button" role="menuitem" onClick={() => { setOpen(false); onRaise() }}>
            <IconCart />
            Raise requirement
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              void navigator.clipboard?.writeText(part.part_number)
              setCopied(true)
              setTimeout(() => setOpen(false), 600)
            }}
          >
            <IconCopy />
            {copied ? 'Copied' : 'Copy part number'}
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * THE CATALOGUE.
 *
 * Every part this operation carries, and the four things someone looking for
 * one has in hand: a name, a number, the machine it has to fit, or how soon
 * it is needed.
 *
 * THE TABLE IS THE PAGE
 * ---------------------
 * This used to open on a row of five tiles — a total, the three largest
 * categories, and a "More" — above a table that then had to fight them for
 * the reader's attention. The tiles were a dashboard on a page that is not
 * one: the question here is never "how is the catalogue distributed", it is
 * "where is the part", and every tile was a category filter the Category
 * facet already offers. They are gone, and what replaces them is one line of
 * measure. The table gets the page.
 *
 * Every number on that line is counted from the rows in hand — not a stored
 * total that can drift from what the table underneath it shows.
 */
export function PartsCatalogue({ machineId, onClearMachine, onOpen, onRaise }: Props) {
  /* The machine the catalogue is standing on, and the ids of the parts that
     fit it. Null until asked for, so the ordinary catalogue costs nothing
     extra. */
  const [machine, setMachine] = useState<MachineDetail | null>(null)
  const [fits, setFits] = useState<Set<string> | null>(null)
  const [search, setSearch] = useState('')
  const [parts, setParts] = useState<PartRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [category, setCategory] = useState('any')
  const [machineFilter, setMachineFilter] = useState('any')
  const [availability, setAvailability] = useState('any')
  const [lead, setLead] = useState('any')
  const [openPicker, setOpenPicker] = useState<string | null>(null)

  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: 'name', asc: true })
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  /* Rows an API a restart behind would leave short of these two fields, so a
     catalogue does not white-screen because the backend has not caught up.
     A part that claims to fit nothing is better than a page that does not
     draw. */
  const normalise = (list: PartRow[]) =>
    list.map((row) => ({ ...row, machines: row.machines ?? [], stock: row.stock ?? null }))

  useEffect(() => {
    let cancelled = false
    // Debounced: typing a part number should not be nine requests.
    const t = setTimeout(() => {
      api
        .listParts(search.trim() || undefined)
        .then((list) => {
          if (cancelled) return
          setParts(normalise(list))
        })
        .catch((err: unknown) => {
          if (cancelled) return
          setError(err instanceof ApiError ? err.message : 'Could not load the catalogue.')
        })
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [search])

  /**
   * The whole catalogue, fetched once and never narrowed.
   *
   * `parts` above is the SEARCH RESULT — the search runs on the server, so
   * once something is typed that list is no longer the catalogue. Measuring
   * the catalogue from it made the summary line report the search: typing
   * "hydraulic" turned "10 parts · 9 categories · 4 machine families" into
   * "2 parts · 1 category · 4 machine families", which is not a measure of
   * anything the reader asked about, and left the result line beside it
   * saying "showing all 2" of a catalogue that has ten.
   *
   * It is also what the facet menus are built from, so searching cannot
   * empty the Category list down to the one category the results happen to
   * be in.
   */
  const [catalogue, setCatalogue] = useState<PartRow[] | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listParts()
      .then((list) => !cancelled && setCatalogue(normalise(list)))
      .catch(() => {
        /* The searched fetch above reports the failure; one error on screen
           is enough, and this list only feeds a caption. */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!machineId) {
      setMachine(null)
      setFits(null)
      return undefined
    }
    let cancelled = false
    Promise.all([api.getMachine(machineId), api.getMachineParts(machineId)])
      .then(([m, list]) => {
        if (cancelled) return
        setMachine(m)
        setFits(new Set(list.map((x) => x.id)))
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load that machine.')
      })
    return () => {
      cancelled = true
    }
  }, [machineId])

  /* Everything the server returned, before the machine narrows it. The
     facets are still built from this, so standing on a machine does not
     empty the category menu down to the categories that happen to fit. */
  const all = useMemo(() => parts ?? [], [parts])

  /* The rows the machine allows. A separate step from the facets below on
     purpose: this one is a RULE, not a preference, and the reader is told
     which of the two is hiding things from them. */
  const inScope = useMemo(
    () => (fits ? all.filter((p) => fits.has(p.id)) : all),
    [all, fits],
  )
  const everything = useMemo(() => catalogue ?? all, [catalogue, all])

  /** Every category the catalogue holds, largest first. */
  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    everything.forEach((p) => counts.set(p.category, (counts.get(p.category) ?? 0) + 1))
    return [...counts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  }, [everything])

  const machines = useMemo(() => {
    const set = new Set<string>()
    everything.forEach((p) => p.machines.forEach((m) => set.add(m)))
    return [...set].sort()
  }, [everything])

  const shown = useMemo(() => {
    let list = inScope
    if (category !== 'any') list = list.filter((p) => p.category === category)
    if (machineFilter !== 'any')
      list = list.filter((p) => p.machines.includes(machineFilter))
    if (availability !== 'any') list = list.filter((p) => availabilityOf(p) === availability)
    if (lead !== 'any') list = list.filter((p) => p.lead_time_days <= Number(lead))
    return [...list].sort((a, b) => {
      /* Three of these columns hold numbers and three hold text, and the
         comparator has to know which: localeCompare on a lead time sorts
         "7" after "30" because it is comparing the characters. */
      let d: number
      if (sort.key === 'availability') {
        d = AVAILABILITY_ORDER[availabilityOf(a)] - AVAILABILITY_ORDER[availabilityOf(b)]
      } else if (sort.key === 'lead_time') {
        d = a.lead_time_days - b.lead_time_days
      } else if (sort.key === 'stock') {
        // No stock record sorts with the empty shelves, not above them.
        d = (onHand(a) ?? -1) - (onHand(b) ?? -1)
      } else {
        d = a[sort.key].localeCompare(b[sort.key])
      }
      // Ties fall back to the name, so a sort by category or availability is
      // stable and readable inside each group rather than in seed order.
      return (sort.asc ? d : -d) || a.name.localeCompare(b.name)
    })
  }, [inScope, category, machineFilter, availability, lead, sort])

  // A filter change can leave the reader on a page that no longer exists.
  useEffect(() => {
    setPage(0)
  }, [shown.length])

  const pages = Math.max(1, Math.ceil(shown.length / PAGE_SIZE))
  const safePage = Math.min(page, pages - 1)
  const rows = shown.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE)
  /* The search counts as narrowing. "Clear filters" clears it along with the
     four facets, so a reader who has typed something and wants back to the
     whole catalogue must be able to see the control that does it. */
  const narrowed =
    category !== 'any' ||
    machineFilter !== 'any' ||
    availability !== 'any' ||
    lead !== 'any' ||
    search.trim() !== ''

  /** How many the catalogue holds, against how many are in front of you. */
  const total = everything.length

  const allOnPageSelected = rows.length > 0 && rows.every((p) => selected.has(p.id))
  const toggleAll = () => {
    const next = new Set(selected)
    if (allOnPageSelected) rows.forEach((p) => next.delete(p.id))
    else rows.forEach((p) => next.add(p.id))
    setSelected(next)
  }
  const toggleOne = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const sortBy = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, asc: !s.asc } : { key, asc: true }))

  const Th = ({ label, sortKey }: { label: string; sortKey: SortKey }) => (
    <th>
      <button
        type="button"
        className="ord__sort"
        onClick={() => sortBy(sortKey)}
        aria-label={`Sort by ${label.toLowerCase()}`}
      >
        {label}
        <span
          className={`ord__sort-mark${sort.key === sortKey ? ' is-on' : ''}${
            sort.key === sortKey && !sort.asc ? ' is-asc' : ''
          }`}
          aria-hidden
        >
          ▾
        </span>
      </button>
    </th>
  )

  if (error) return <p className="ord__error">{error}</p>

  const clearAll = () => {
    setCategory('any')
    setMachineFilter('any')
    setAvailability('any')
    setLead('any')
    setSearch('')
  }

  return (
    <>
      {/* THE CONTROL AREA.
          One panel, not a row of loose controls above a bare table: finding a
          part is the whole job of this page, and the things you find it with
          belong together as one object rather than scattered along an edge.
          The search field is given the width because a part number is what
          people arrive holding; the four facets narrow what the number did
          not. */}
      <section className="ord__cat-controls" aria-label="Find a part">
        <div className="ord__cat-search">
          <IconSearch />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by part number, name, category or machine..."
            aria-label="Search the catalogue"
          />
        </div>

        <div className="ord__cat-facets">
          <Picker
            label="Category"
            value={category}
            onChange={setCategory}
            open={openPicker === 'category'}
            setOpen={(v) => setOpenPicker(v ? 'category' : null)}
            options={[
              { value: 'any', label: 'All categories' },
              ...categories.map((c) => ({ value: c.name, label: `${c.name} (${c.count})` })),
            ]}
          />

          {/* The model facet, which is a preference. Distinct from standing on
              a machine, which is a rule — see the scope bar above. */}
          <Picker
            label="Machine"
            value={machineFilter}
            onChange={setMachineFilter}
            open={openPicker === 'machine'}
            setOpen={(v) => setOpenPicker(v ? 'machine' : null)}
            options={[
              { value: 'any', label: 'All machines' },
              ...machines.map((m) => ({ value: m, label: m })),
            ]}
          />

          <Picker
            label="Availability"
            value={availability}
            onChange={setAvailability}
            open={openPicker === 'availability'}
            setOpen={(v) => setOpenPicker(v ? 'availability' : null)}
            options={[
              { value: 'any', label: 'Any availability' },
              { value: 'in', label: 'In stock' },
              { value: 'limited', label: 'Limited stock' },
              { value: 'out', label: 'Out of stock' },
            ]}
          />

          {/* Lead time is a facet like the other three now, rather than the
              one filter hidden behind a "More filters" button. It answers
              "can I have it in time", which on a machine that is down is not
              a secondary question. */}
          <Picker
            label="Lead time"
            value={lead}
            onChange={setLead}
            open={openPicker === 'lead'}
            setOpen={(v) => setOpenPicker(v ? 'lead' : null)}
            options={[
              { value: 'any', label: 'Any lead time' },
              { value: '7', label: 'Within 7 days' },
              { value: '14', label: 'Within 14 days' },
              { value: '30', label: 'Within 30 days' },
            ]}
          />

          {/* Only once there is something to clear. A permanently-lit "Clear
              filters" on an unfiltered catalogue is a control that does
              nothing, and it reads as one. */}
          {narrowed && (
            <button type="button" className="ord__cat-clear" onClick={clearAll}>
              Clear filters
            </button>
          )}
        </div>
      </section>

      {/* ALL PARTS, or PARTS THAT FIT THIS MACHINE. The distinction is the
          whole point of the machine-aware catalogue, so it is stated rather
          than left to be inferred from a shorter list. */}
      {machine && (
        <div className="ord__scope">
          <span className="ord__scope-label">Parts that fit</span>
          <span className="ord__scope-machine">
            {machine.serial_number}
            <span className="ord__scope-model">{machine.model}</span>
          </span>
          <button type="button" className="ord__scope-clear" onClick={onClearMachine}>
            Show all parts
          </button>
        </div>
      )}

      {parts === null ? (
        <p className="ord__muted">Loading…</p>
      ) : (
        <>
          {/* THE MEASURE OF THE CATALOGUE.
              Counted from the rows in hand, never written down: the parts,
              the categories they fall into, and the machine families they are
              listed against. The result line beside it reports the filtered
              view, so the two together say "this much exists, this much is in
              front of you". */}
          <div className="ord__cat-measure">
            <p className="ord__cat-summary">
              <span className="ord__cat-figure">{total}</span> part
              {total === 1 ? '' : 's'}
              <span className="ord__cat-sep" aria-hidden>
                ·
              </span>
              <span className="ord__cat-figure">{categories.length}</span> categor
              {categories.length === 1 ? 'y' : 'ies'}
              <span className="ord__cat-sep" aria-hidden>
                ·
              </span>
              <span className="ord__cat-figure">{machines.length}</span> machine famil
              {machines.length === 1 ? 'y' : 'ies'}
            </p>

            <p className="ord__cat-result" role="status">
              {machine
                ? `${shown.length} of ${total} fit this machine`
                : shown.length === total
                  ? `Showing all ${total}`
                  : `${shown.length} of ${total} shown`}
            </p>
          </div>

          {selected.size > 0 && (
            <div className="ord__selection">
              <span>
                <strong>{selected.size}</strong> part{selected.size === 1 ? '' : 's'} selected
              </span>
              <button
                type="button"
                className="ord__tool-btn"
                disabled={selected.size !== 1}
                title={
                  selected.size === 1
                    ? undefined
                    : 'A requirement is raised for one part on one machine — select a single part.'
                }
                onClick={() => onRaise([...selected][0])}
              >
                <IconCart />
                Raise requirement
              </button>
              <button
                type="button"
                className="ord__tool-btn"
                onClick={() => setSelected(new Set())}
              >
                Clear selection
              </button>
            </div>
          )}

          {rows.length === 0 ? (
            <div className="ord__empty">
              <p className="ord__empty-title">Nothing here</p>
              <p className="ord__empty-body">
                {machine && inScope.length === 0
                  ? `No part in this catalogue is listed as fitting a ${machine.model}.`
                  : search.trim()
                    ? `No part matches “${search.trim()}”.`
                    : 'No part matches those filters.'}{' '}
                {narrowed ? 'Clearing them will bring the rest back.' : ''}
              </p>
            </div>
          ) : (
            <div className="ord__card ord__card--table">
              <table className="ord__table ord__table--cat">
                <thead>
                  <tr>
                    <th className="ord__th-check">
                      <input
                        type="checkbox"
                        checked={allOnPageSelected}
                        onChange={toggleAll}
                        aria-label="Select every part on this page"
                      />
                    </th>
                    <Th label="Part number" sortKey="part_number" />
                    <Th label="Part" sortKey="name" />
                    <Th label="Category" sortKey="category" />
                    <th>Machine / fitment</th>
                    <Th label="Availability" sortKey="availability" />
                    <Th label="Lead time" sortKey="lead_time" />
                    <Th label="Stock" sortKey="stock" />
                    <th className="ord__th-actions">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => {
                    const thumb = thumbnailFor(p.id)
                    const avail = availabilityOf(p)
                    const qty = onHand(p)
                    // "All models" is a claim about this catalogue's own
                    // fitment records, not a promise about every machine
                    // Hitachi builds — so it is only said when the part is
                    // in fact listed against every model the catalogue knows.
                    const fitsAll =
                      machines.length > 0 && p.machines.length === machines.length
                    // One model and a count, not the whole list. Two were
                    // listed here and neither fitted: "ZX350LC-7,
                    // ZX490LCH-7" is 21 characters in a cell that holds
                    // about twelve, so the second model was clipped mid-word
                    // on every row that had one. One model names the family
                    // and the count says how many more — and the Machine
                    // facet above answers "does it fit mine" exactly.
                    const listed = p.machines.slice(0, 1)
                    const rest = p.machines.length - listed.length
                    return (
                      <tr
                        key={p.id}
                        tabIndex={0}
                        aria-label={`Open the record for ${p.name}`}
                        onClick={() => onOpen(p.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            onOpen(p.id)
                          }
                        }}
                      >
                        <td className="ord__td-check" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selected.has(p.id)}
                            onChange={() => toggleOne(p.id)}
                            aria-label={`Select ${p.name}`}
                          />
                        </td>

                        {/* The number a dealer quotes, set apart from the
                            prose around it so the eye can run down the column
                            without reading any of it. */}
                        <td className="ord__td-partno">{p.part_number}</td>

                        {/* The loudest thing in the row. A hydraulic pump and
                            a filter are told apart by shape long before
                            either name is read, so the picture travels with
                            the name rather than in a column of its own. */}
                        <td className="ord__td-part">
                          <span className="ord__part-cell">
                            <span className="ord__thumb ord__thumb--row">
                              {thumb ? <img src={thumb} alt="" loading="lazy" /> : null}
                            </span>
                            <span className="ord__part-name">{p.name}</span>
                          </span>
                        </td>

                        <td className="ord__td-quiet">{p.category}</td>

                        <td className="ord__td-quiet">
                          {p.machines.length === 0 ? (
                            <span className="ord__muted-cell">—</span>
                          ) : fitsAll ? (
                            <span className="ord__fit">All models</span>
                          ) : (
                            <span className="ord__fits">
                              <span className="ord__fit">{listed.join(', ')}</span>
                              {rest > 0 && <span className="ord__fit is-rest">+{rest}</span>}
                            </span>
                          )}
                        </td>

                        <td>
                          <span className={`ord__avail is-${avail}`}>
                            <span className="ord__avail-dot" aria-hidden />
                            {AVAILABILITY_LABEL[avail]}
                          </span>
                        </td>

                        <td className="ord__td-lead">
                          {p.lead_time_days} <span className="ord__unit">days</span>
                        </td>

                        {/* Availability says whether it can be had; this says
                            how much, and where from. Same source, different
                            question — the status word cannot be counted and
                            the count cannot be scanned. */}
                        <td className="ord__td-stock">
                          {qty === null || !p.stock ? (
                            <span className="ord__muted-cell">Not stocked</span>
                          ) : (
                            <span className={`ord__stock is-${avail}`}>
                              <span className="ord__stock-qty">{qty}</span>
                              <span className="ord__stock-where">{p.stock.warehouse}</span>
                            </span>
                          )}
                        </td>

                        <td className="ord__row-actions" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            className="ord__icon-btn"
                            aria-label={`View the record for ${p.name}`}
                            onClick={() => onOpen(p.id)}
                          >
                            <IconEye />
                          </button>
                          <button
                            type="button"
                            className="ord__icon-btn"
                            aria-label={`Raise a requirement for ${p.name}`}
                            onClick={() => onRaise(p.id)}
                          >
                            <IconCart />
                          </button>
                          <RowMenu
                            part={p}
                            onOpen={() => onOpen(p.id)}
                            onRaise={() => onRaise(p.id)}
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              <div className="ord__table-foot">
                <span className="ord__muted">
                  Showing {safePage * PAGE_SIZE + 1} – {safePage * PAGE_SIZE + rows.length} of{' '}
                  {shown.length} part{shown.length === 1 ? '' : 's'}
                </span>
                <div className="ord__pager">
                  <button
                    type="button"
                    className="ord__icon-btn"
                    aria-label="Previous page"
                    disabled={safePage === 0}
                    onClick={() => setPage(safePage - 1)}
                  >
                    <IconChevronLeft />
                  </button>
                  {pageList(pages, safePage).map((n, i) =>
                    n === '…' ? (
                      <span key={`gap-${i}`} className="ord__page-gap" aria-hidden>
                        …
                      </span>
                    ) : (
                      <button
                        key={n}
                        type="button"
                        className={`ord__page${n === safePage ? ' is-current' : ''}`}
                        aria-current={n === safePage ? 'page' : undefined}
                        onClick={() => setPage(n)}
                      >
                        {n + 1}
                      </button>
                    ),
                  )}
                  <button
                    type="button"
                    className="ord__icon-btn"
                    aria-label="Next page"
                    disabled={safePage === pages - 1}
                    onClick={() => setPage(safePage + 1)}
                  >
                    <IconChevronRight />
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}
