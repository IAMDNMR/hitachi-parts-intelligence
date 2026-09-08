import { useEffect, useRef, useState } from 'react'
import { STAGE_LABELS } from '../types'
import type { Requirement, Stage } from '../types'
import { thumbnailFor } from '../thumbnails'
import {
  IconCheckCircle,
  IconChevronLeft,
  IconChevronRight,
  IconDots,
  IconEdit,
  IconEye,
  IconHourglass,
  IconTrash,
  IconTruck,
} from './Icons'

const PAGE_SIZE = 10

/** A glyph per stage, so a status reads before it is read. */
function StageIcon({ stage }: { stage: Stage }) {
  if (stage === 'received') return <IconCheckCircle />
  if (stage === 'shipped') return <IconTruck />
  return <IconHourglass />
}

/**
 * "2 days ago" alongside the date.
 *
 * The absolute date answers "when", the relative one answers "is this
 * stale" — which is the question someone scanning a work list is actually
 * asking, and the one a date alone makes them do arithmetic for.
 */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  const days = Math.floor((Date.now() - then) / 86_400_000)
  if (days <= 0) {
    const hours = Math.floor((Date.now() - then) / 3_600_000)
    if (hours <= 0) return 'just now'
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  }
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days} days ago`
  const months = Math.round(days / 30)
  return months === 1 ? '1 month ago' : `${months} months ago`
}

/**
 * Machine class from the serial.
 *
 * Every machine in this model is a Hitachi Zaxis, which is an excavator —
 * but that is read off the serial rather than assumed, so a serial from
 * some other range does not get silently labelled as something it is not.
 */
function machineClass(serial: string): string | null {
  return /^ZX/i.test(serial) ? 'Excavator' : null
}

function RowMenu({
  requirement,
  editable,
  onOpen,
  onEdit,
  onCancel,
}: {
  requirement: Requirement
  editable: boolean
  onOpen: () => void
  onEdit: () => void
  onCancel: () => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Closes on an outside click or Escape — a menu that can only be shut by
  // choosing something from it is a trap.
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
        aria-label={`Actions for requirement #${requirement.id}`}
        onClick={() => setOpen((v) => !v)}
      >
        <IconDots />
      </button>
      {open && (
        <div className="ord__menu-pop" role="menu">
          <button type="button" role="menuitem" onClick={() => { setOpen(false); onOpen() }}>
            <IconEye />
            View
          </button>
          {editable && (
            <button type="button" role="menuitem" onClick={() => { setOpen(false); onEdit() }}>
              <IconEdit />
              Edit
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            className="is-danger"
            onClick={() => { setOpen(false); onCancel() }}
          >
            <IconTrash />
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}

export function RequirementsTable({
  requirements,
  filtered,
  onOpen,
  onEdit,
  onCancel,
}: {
  requirements: Requirement[] | null
  filtered: boolean
  onOpen: (id: number) => void
  onEdit: (id: number) => void
  onCancel: (r: Requirement) => void
}) {
  const [page, setPage] = useState(0)
  const [sortNewestFirst, setSortNewestFirst] = useState(true)

  // A filter change can leave the reader on a page that no longer exists.
  useEffect(() => {
    setPage(0)
  }, [requirements?.length, filtered])

  if (requirements === null) return <p className="ord__muted">Loading…</p>
  if (requirements.length === 0) {
    return (
      <div className="ord__empty">
        <p className="ord__empty-title">{filtered ? 'Nothing here' : 'Nothing raised yet'}</p>
        <p className="ord__empty-body">
          {filtered
            ? 'No requirement matches what you are looking for. Try another filter, or clear the search.'
            : 'A part is needed for a machine — that is where this process begins. “New requirement” starts one.'}
        </p>
      </div>
    )
  }

  const sorted = [...requirements].sort((a, b) => {
    const d = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    return sortNewestFirst ? d : -d
  })
  const pages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const safePage = Math.min(page, pages - 1)
  const rows = sorted.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE)

  return (
    <div className="ord__card">
      <table className="ord__table">
        <thead>
          <tr>
            <th>#</th>
            <th>Part</th>
            <th>Qty</th>
            <th>Machine</th>
            <th>Stage</th>
            <th>
              <button
                type="button"
                className="ord__sort"
                onClick={() => setSortNewestFirst((v) => !v)}
                aria-label={`Sort by date raised, ${sortNewestFirst ? 'oldest' : 'newest'} first`}
              >
                Raised
                <span className={`ord__sort-mark${sortNewestFirst ? '' : ' is-asc'}`} aria-hidden>
                  ▾
                </span>
              </button>
            </th>
            <th className="ord__th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const editable =
              r.stage === 'identified' ||
              r.stage === 'availability_checked' ||
              r.stage === 'ordered'
            const thumb = thumbnailFor(r.part.id)
            const klass = machineClass(r.machine_serial)
            return (
              <tr
                key={r.id}
                tabIndex={0}
                onClick={() => onOpen(r.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onOpen(r.id)
                  }
                }}
              >
                <td className="ord__mono">{String(r.id).padStart(4, '0')}</td>
                <td>
                  <span className="ord__part-cell">
                    <span className="ord__thumb">
                      {thumb ? <img src={thumb} alt="" loading="lazy" /> : null}
                    </span>
                    <span>
                      <span className="ord__cell-main">{r.part.name}</span>
                      <span className="ord__cell-sub">{r.part.part_number}</span>
                    </span>
                  </span>
                </td>
                <td>{r.quantity}</td>
                <td>
                  <span className="ord__cell-main">{r.machine_serial}</span>
                  {klass && <span className="ord__cell-sub">{klass}</span>}
                </td>
                <td>
                  <span className={`ord__stage-pill is-${r.stage}`}>
                    <StageIcon stage={r.stage} />
                    {STAGE_LABELS[r.stage]}
                  </span>
                </td>
                <td>
                  <span className="ord__cell-main ord__cell-date">
                    {new Date(r.created_at).toLocaleDateString(undefined, {
                      dateStyle: 'medium',
                    })}
                  </span>
                  <span className="ord__cell-sub">{relativeTime(r.created_at)}</span>
                </td>
                <td className="ord__row-actions" onClick={(e) => e.stopPropagation()}>
                  <RowMenu
                    requirement={r}
                    editable={editable}
                    onOpen={() => onOpen(r.id)}
                    onEdit={() => onEdit(r.id)}
                    onCancel={() => onCancel(r)}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="ord__table-foot">
        <span className="ord__muted">
          Showing {rows.length} of {sorted.length} requirement{sorted.length === 1 ? '' : 's'}
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
            {Array.from({ length: pages }, (_, i) => (
              <button
                key={i}
                type="button"
                className={`ord__page${i === safePage ? ' is-current' : ''}`}
                aria-current={i === safePage ? 'page' : undefined}
                onClick={() => setPage(i)}
              >
                {i + 1}
              </button>
            ))}
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
  )
}
