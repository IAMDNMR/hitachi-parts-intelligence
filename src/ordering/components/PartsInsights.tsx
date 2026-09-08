import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../api'
import { STAGE_LABELS, STAGE_SEQUENCE } from '../types'
import type { PartRow, Requirement, Stage } from '../types'
import { thumbnailFor } from '../thumbnails'
import { IconBack } from './Icons'

/**
 * Parts insights.
 *
 * Exists because the alternative was a "View analytics" button that did
 * nothing, which is exactly the kind of thing that makes an interface feel
 * like a mock-up of an application rather than one.
 *
 * Everything here is derived from records this service already holds — the
 * requirements raised and the stock on the shelves. Nothing is estimated,
 * projected or invented: where there is no data yet the panel says so
 * rather than drawing an empty chart with confident axes.
 */
export function PartsInsights({ onBack }: { onBack: () => void }) {
  const [requirements, setRequirements] = useState<Requirement[] | null>(null)
  /**
   * PartRow, not Part.
   *
   * The catalogue endpoint already returns the lead time and the stock level
   * on every row. Typing this as the narrower `Part` threw both away, which
   * is why the lead-time column below printed an em dash for every part on a
   * panel whose own strapline promises lead times — and why the stock had to
   * be fetched again, one request per part, to get back what the first
   * request had already sent.
   */
  const [parts, setParts] = useState<PartRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([api.listRequirements(), api.listParts()])
      .then(([reqs, ps]) => {
        if (cancelled) return
        setRequirements(reqs)
        setParts(ps)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load insights.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const demand = useMemo(() => {
    const counts = new Map<string, { name: string; id: string; units: number; raised: number }>()
    ;(requirements ?? []).forEach((r) => {
      const row = counts.get(r.part.id) ?? {
        name: r.part.name,
        id: r.part.id,
        units: 0,
        raised: 0,
      }
      row.units += r.quantity
      row.raised += 1
      counts.set(r.part.id, row)
    })
    return [...counts.values()].sort((a, b) => b.units - a.units)
  }, [requirements])

  const byStage = useMemo(() => {
    const counts = new Map<Stage, number>()
    ;(requirements ?? []).forEach((r) => counts.set(r.stage, (counts.get(r.stage) ?? 0) + 1))
    return STAGE_SEQUENCE.map((s) => ({ stage: s, count: counts.get(s) ?? 0 }))
  }, [requirements])

  const lowStock = useMemo(
    () =>
      (parts ?? [])
        .map((p) => ({
          part: p,
          qty: p.stock?.qty_on_hand ?? 0,
          reorder: p.stock?.reorder_point ?? 0,
        }))
        .filter((row) => row.qty <= row.reorder)
        .sort((a, b) => a.qty - b.qty),
    [parts],
  )

  if (error) return <p className="ord__error">{error}</p>
  if (!requirements || !parts) return <p className="ord__muted">Loading…</p>

  const maxUnits = Math.max(1, ...demand.map((d) => d.units))
  const maxStage = Math.max(1, ...byStage.map((s) => s.count))

  return (
    <div>
      <button type="button" className="ord__btn ord__btn--ghost ord__back" onClick={onBack}>
        <IconBack />
        Requirements
      </button>

      <div className="ord__insights">
        <section className="ord__panel">
          <h2 className="ord__panel-title">Demand by part</h2>
          <p className="ord__panel-sub">Units requested across every requirement raised.</p>
          {demand.length === 0 ? (
            <p className="ord__muted">
              Nothing has been requested yet, so there is no demand to report.
            </p>
          ) : (
            <ul className="ord__bars">
              {demand.map((d) => (
                <li key={d.id}>
                  <span className="ord__bar-head">
                    <span className="ord__thumb ord__thumb--sm">
                      {thumbnailFor(d.id) ? <img src={thumbnailFor(d.id)} alt="" /> : null}
                    </span>
                    <span className="ord__bar-name">{d.name}</span>
                    <span className="ord__bar-value">
                      {d.units} <span className="ord__muted">{d.units === 1 ? 'unit' : 'units'}</span>
                    </span>
                  </span>
                  <span className="ord__bar-track">
                    <span
                      className="ord__bar-fill"
                      style={{ width: `${(d.units / maxUnits) * 100}%` }}
                    />
                  </span>
                  <span className="ord__bar-foot">
                    {d.raised} requirement{d.raised === 1 ? '' : 's'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="ord__panel">
          <h2 className="ord__panel-title">Where the work is</h2>
          <p className="ord__panel-sub">
            Requirements at each of the seven stages, in order.
          </p>
          <ul className="ord__bars ord__bars--compact">
            {byStage.map((s) => (
              <li key={s.stage}>
                <span className="ord__bar-head">
                  <span className="ord__bar-name">{STAGE_LABELS[s.stage]}</span>
                  <span className="ord__bar-value">{s.count}</span>
                </span>
                <span className="ord__bar-track">
                  <span
                    className={`ord__bar-fill${s.count === 0 ? ' is-empty' : ''}`}
                    style={{ width: `${(s.count / maxStage) * 100}%` }}
                  />
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="ord__panel">
          <h2 className="ord__panel-title">At or below reorder point</h2>
          <p className="ord__panel-sub">
            Parts that cannot cover another requirement of any size without being
            replenished first.
          </p>
          {lowStock.length === 0 ? (
            <p className="ord__muted">Every part is above its reorder point.</p>
          ) : (
            <table className="ord__table">
              <thead>
                <tr>
                  <th>Part</th>
                  <th>On hand</th>
                  <th>Reorder at</th>
                  <th>Lead time</th>
                </tr>
              </thead>
              <tbody>
                {lowStock.map((row) => (
                  <tr key={row.part.id}>
                    <td>
                      <span className="ord__cell-main">{row.part.name}</span>
                      <span className="ord__cell-sub">{row.part.part_number}</span>
                    </td>
                    <td>
                      <span className={row.qty === 0 ? 'ord__flag' : undefined}>{row.qty}</span>
                    </td>
                    <td className="ord__muted-cell">{row.reorder}</td>
                    <td className="ord__muted-cell">{row.part.lead_time_days} days</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  )
}
