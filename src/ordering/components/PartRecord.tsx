import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { IconMinus, IconPlus } from './Icons'
import { STAGE_LABELS } from '../types'
import { thumbnailFor } from '../thumbnails'
import type { PartDetail, PartUsage } from '../types'

interface Props {
  partId: string
  onBack: () => void
  onRaise: (partId: string) => void
  /** Opens another part's record — used by the supersession link, which is
   *  the one place a part record points at a different part. */
  onOpenPart: (partId: string) => void
  /** The other half of the first real bidirectional relationship in this
   *  product: Machine → Parts, and now Part → Machines. */
  onOpenMachine: (machineId: string) => void
}

type Tab = 'overview' | 'fitment' | 'documents' | 'usage'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'fitment', label: 'Fits' },
  { id: 'documents', label: 'Documents' },
  { id: 'usage', label: 'Machines that needed it' },
]

/**
 * The part record.
 *
 * Modelled on how an engineering PLM lays a part out — identity at the top,
 * tabs for the different things you can ask about it — but the questions
 * are after-sales' own. There is no bill of materials here, no CAD source
 * and no design revision, because none of those exist once the machine is
 * built and working. What replaces them: what the part FITS, what it
 * SUPERSEDES, how long it takes to GET, and which machines have actually
 * needed one.
 */
export function PartRecord({
  partId,
  onBack,
  onRaise,
  onOpenPart,
  onOpenMachine,
}: Props) {
  const [part, setPart] = useState<PartDetail | null>(null)
  const [usage, setUsage] = useState<PartUsage[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('overview')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setPart(null)
    setError(null)
    Promise.all([api.getPart(partId), api.getPartUsage(partId)])
      .then(([p, u]) => {
        if (cancelled) return
        setPart(p)
        setUsage(u)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load that part.')
      })
    return () => {
      cancelled = true
    }
  }, [partId])

  if (error) return <p className="ord__error">{error}</p>
  if (!part) return <p className="ord__muted">Loading…</p>

  const stock = part.stock
  const belowReorder = stock ? stock.qty_on_hand <= stock.reorder_point : false
  const thumb = thumbnailFor(part.id)
  /** Set only when this record IS the dead number. */
  const replacedBy = part.superseded_by
  /* The same three states the catalogue row reports, read the same way off
     the same two numbers — see availabilityOf in PartsCatalogue. A reader
     arriving here from a row marked "Limited" must not find a record that
     describes the shelf differently. */
  const availability: 'in' | 'limited' | 'out' = !stock || stock.qty_on_hand <= 0
    ? 'out'
    : belowReorder
      ? 'limited'
      : 'in'
  const AVAILABILITY_LABEL = {
    in: 'In stock',
    limited: 'Limited',
    out: 'Out of stock',
  } as const

  const adjust = async (delta: number) => {
    setBusy(true)
    setError(null)
    try {
      const next = await api.adjustStock(part.id, delta)
      setPart({ ...part, stock: next })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not adjust stock.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ord__record">
      <button type="button" className="ord__btn ord__btn--ghost ord__back" onClick={onBack}>
        ← Parts catalogue
      </button>

      {/* The head is built out of the pieces of the row that was clicked to
          reach it — the same photograph, the same part number treatment, the
          same availability dot — so the record reads as that row opened up
          rather than as a different screen about the same part. */}
      <header className="ord__record-head">
        <span className="ord__thumb ord__thumb--record">
          {thumb ? <img src={thumb} alt="" /> : null}
        </span>

        <div className="ord__record-ident">
          <span className="ord__partno">{part.part_number}</span>
          <h2 className="ord__record-title">{part.name}</h2>
          <p className="ord__record-desc">{part.description}</p>
          <div className="ord__chips">
            {/* A superseded number is not "out of stock" — nobody is going to
                restock it. Saying so would send someone away to wait for a
                delivery that is never coming, and a 0-day lead time beside it
                reads as "available now", which is the opposite of the truth. */}
            <span className={`ord__avail is-${replacedBy ? 'out' : availability}`}>
              <span className="ord__avail-dot" aria-hidden />
              {replacedBy ? 'Not supplied' : AVAILABILITY_LABEL[availability]}
              {!replacedBy && stock && ` — ${stock.qty_on_hand} at ${stock.warehouse}`}
            </span>
            <span className="ord__chip">{part.category}</span>
            {!replacedBy && (
              <span className="ord__chip">Lead time {part.lead_time_days} days</span>
            )}
            {part.supersedes && (
              <span className="ord__chip is-warn">Supersedes {part.supersedes.part_number}</span>
            )}
          </div>
        </div>

        {/* A superseded number cannot be ordered.
            Offering "Raise requirement" here would let someone raise one
            against a part that is no longer supplied — which is the exact
            mistake keeping the old row is meant to prevent. The action is
            replaced by the answer they actually came for: the number that
            replaced it. */}
        {replacedBy ? (
          <button
            type="button"
            className="ord__btn"
            onClick={() => onOpenPart(replacedBy.id)}
          >
            Go to {replacedBy.part_number}
          </button>
        ) : (
          <button type="button" className="ord__btn" onClick={() => onRaise(part.id)}>
            Raise requirement
          </button>
        )}
      </header>

      {replacedBy && (
        <p className="ord__note">
          This number is no longer supplied. It is kept because machines in the field still
          carry it on their labels — order <strong>{replacedBy.part_number}</strong> instead.
        </p>
      )}

      <nav className="ord__tabs" aria-label="Part record sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`ord__tab${tab === t.id ? ' is-current' : ''}`}
            aria-current={tab === t.id ? 'true' : undefined}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.id === 'fitment' && ` (${part.fitments.length})`}
            {t.id === 'documents' && ` (${part.documents.length})`}
            {t.id === 'usage' && usage && ` (${usage.length})`}
          </button>
        ))}
      </nav>

      {tab === 'overview' && (
        <dl className="ord__facts">
          <div>
            <dt>Part number</dt>
            <dd>{part.part_number}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{part.category}</dd>
          </div>
          <div>
            <dt>Lead time</dt>
            <dd>{replacedBy ? 'Not supplied' : `${part.lead_time_days} days`}</dd>
          </div>
          <div>
            <dt>On hand</dt>
            <dd>
              {stock ? `${stock.qty_on_hand} at ${stock.warehouse}` : 'No stock record'}
              {stock && belowReorder && (
                <span className="ord__flag"> — at or below reorder point ({stock.reorder_point})</span>
              )}
              {stock && (
                <span className="ord__stock-adjust">
                  <button
                    type="button"
                    className="ord__icon-btn"
                    title="Receive one in"
                    aria-label="Receive one into stock"
                    disabled={busy}
                    onClick={() => adjust(1)}
                  >
                    <IconPlus />
                  </button>
                  <button
                    type="button"
                    className="ord__icon-btn"
                    title="Take one out"
                    aria-label="Take one out of stock"
                    disabled={busy || stock.qty_on_hand === 0}
                    onClick={() => adjust(-1)}
                  >
                    <IconMinus />
                  </button>
                </span>
              )}
            </dd>
          </div>
          {/* The old number is a link, not a caption. It is the only reason
              the superseded row is kept in the catalogue at all: a machine in
              the field carries the old number on its label, someone reads it
              off, and it has to resolve. */}
          <div>
            <dt>Supersedes</dt>
            <dd>
              {part.supersedes ? (
                <button
                  type="button"
                  className="ord__link"
                  onClick={() => onOpenPart(part.supersedes!.id)}
                >
                  {part.supersedes.part_number} — {part.supersedes.name}
                </button>
              ) : (
                'Nothing — this is the original number'
              )}
            </dd>
          </div>
        </dl>
      )}

      {tab === 'fitment' && (
        <div className="ord__card">
        <table className="ord__table">
          <thead>
            <tr>
              <th>Machine model</th>
              <th>Where it sits</th>
            </tr>
          </thead>
          <tbody>
            {part.fitments.map((f) => (
              <tr key={`${f.machine_model}-${f.assembly}`}>
                <td>{f.machine_model}</td>
                <td>{f.assembly}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {tab === 'documents' &&
        (part.documents.length === 0 ? (
          <p className="ord__muted">No bulletins or fitting instructions for this part.</p>
        ) : (
          <ul className="ord__docs">
            {part.documents.map((d) => (
              <li key={d.reference}>
                <span className="ord__chip">{d.doc_type}</span>
                <span className="ord__doc-title">{d.title}</span>
                <span className="ord__doc-ref">{d.reference}</span>
              </li>
            ))}
          </ul>
        ))}

      {tab === 'usage' &&
        (usage === null ? (
          <p className="ord__muted">Loading…</p>
        ) : usage.length === 0 ? (
          <p className="ord__muted">
            No requirement has been raised against this part yet.
          </p>
        ) : (
          <div className="ord__card">
          <table className="ord__table">
            <thead>
              <tr>
                <th>#</th>
                <th>Machine</th>
                <th>Qty</th>
                <th>Stage</th>
                <th>Raised</th>
              </tr>
            </thead>
            <tbody>
              {usage.map((u) => (
                <tr key={u.requirement_id}>
                  <td>{u.requirement_id}</td>
                  <td>
                    <button
                      type="button"
                      className="ord__link"
                      onClick={() => onOpenMachine(u.machine_id)}
                    >
                      {u.machine_serial}
                    </button>
                    <span className="ord__cell-sub">{u.machine_model}</span>
                  </td>
                  <td>{u.quantity}</td>
                  <td>
                    <span className={`ord__stage-pill is-${u.stage}`}>
                      {STAGE_LABELS[u.stage]}
                    </span>
                  </td>
                  <td>
                    {new Date(u.created_at).toLocaleDateString(undefined, {
                      dateStyle: 'medium',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ))}
    </div>
  )
}
