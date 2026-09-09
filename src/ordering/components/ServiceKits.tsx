import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { Kit, KitDetail } from '../types'
import { thumbnailFor } from '../thumbnails'
import { IconBack, IconCart, IconCheckCircle, IconHourglass } from './Icons'

/**
 * SERVICE KITS.
 *
 * The planned half of a parts operation.
 *
 * Everything else in this tool is reactive: something failed, somebody raised
 * a requirement for the part. A kit is the other half — the parts a known job
 * consumes, ordered together, before anything has broken. It is also most of
 * what a healthy after-sales parts business actually sells, and until now the
 * tool could not express it at all: a five-hundred-hour service had to be
 * raised one line at a time by somebody who already knew the list.
 *
 * Two numbers do the work on this screen, and neither is the part count.
 *
 *   READY      every line coverable from the shelf today. A service that
 *              arrives four-fifths complete has not arrived, so this is
 *              judged against the quantity the KIT calls for, not against
 *              whether the part exists — a kit needing two of something with
 *              one on hand is short.
 *
 *   SLOWEST    the longest lead time in the kit, never the average. A service
 *              lands when its last part does; averaging flatters it by weeks.
 *
 * Both are answered before the button is pressed, because they are what a
 * service date gets committed against.
 */
interface Props {
  onRaised: (machineSerial: string, count: number) => void
}

export function ServiceKits({ onRaised }: Props) {
  const [kits, setKits] = useState<Kit[] | null>(null)
  const [open, setOpen] = useState<KitDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listKits()
      .then((list) => !cancelled && setKits(list))
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load the service kits.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) return <p className="ord__error">{error}</p>
  if (!kits) return <p className="ord__muted">Loading…</p>

  if (open) {
    return <KitRecord kit={open} onBack={() => setOpen(null)} onRaised={onRaised} />
  }

  const scheduled = kits.filter((k) => k.interval_hours !== null)
  const repairs = kits.filter((k) => k.interval_hours === null)

  return (
    <>
      {/* Split by kind, because the two are ordered for different reasons.
          A scheduled kit recurs and can be planned months out; a repair kit
          is wanted the day the job is booked. Listing them together would
          bury the only ones that can be forecast. */}
      <KitGroup
        title="Scheduled maintenance"
        note="Recurs on machine hours for the life of the machine. This is the demand that can be forecast."
        kits={scheduled}
        onOpen={setOpen}
        setError={setError}
      />
      <KitGroup
        title="Repair kits"
        note="The parts a particular job consumes, gathered so nobody discovers the fifth one on the day."
        kits={repairs}
        onOpen={setOpen}
        setError={setError}
      />
    </>
  )
}

function KitGroup({
  title,
  note,
  kits,
  onOpen,
  setError,
}: {
  title: string
  note: string
  kits: Kit[]
  onOpen: (k: KitDetail) => void
  setError: (m: string) => void
}) {
  if (kits.length === 0) return null

  const open = async (id: string) => {
    try {
      onOpen(await api.getKit(id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not open that kit.')
    }
  }

  return (
    <section className="ord__kit-group">
      <header className="ord__kit-group-head">
        <h2 className="ord__kit-group-title">{title}</h2>
        <p className="ord__kit-group-note">{note}</p>
      </header>

      <div className="ord__kits">
        {kits.map((kit) => (
          <button
            key={kit.id}
            type="button"
            className="ord__kit"
            onClick={() => void open(kit.id)}
          >
            <span className="ord__kit-code">{kit.code}</span>
            <span className="ord__kit-name">{kit.name}</span>
            <span className="ord__kit-desc">{kit.description}</span>

            <span className="ord__kit-facts">
              {kit.interval_hours !== null && (
                <span className="ord__kit-fact">
                  <b>{kit.interval_hours.toLocaleString()}</b> hours
                </span>
              )}
              <span className="ord__kit-fact">
                <b>{kit.line_count}</b> {kit.line_count === 1 ? 'part' : 'parts'}
              </span>
              <span className="ord__kit-fact">
                <b>{kit.longest_lead_days}</b> days at worst
              </span>
            </span>

            <span className={`ord__kit-ready is-${kit.ready ? 'yes' : 'no'}`}>
              {kit.ready ? <IconCheckCircle /> : <IconHourglass />}
              {kit.ready ? 'Every part on the shelf' : 'Short — one or more lines'}
            </span>

            <span className="ord__kit-fits">{kit.machines.join(' · ')}</span>
          </button>
        ))}
      </div>
    </section>
  )
}

/**
 * One kit, and the button that raises it.
 *
 * The machine serial is asked for here rather than assumed, because a kit is
 * a template — the same five-hundred-hour service is raised against a
 * different machine every week.
 */
function KitRecord({
  kit,
  onBack,
  onRaised,
}: {
  kit: KitDetail
  onBack: () => void
  onRaised: (machineSerial: string, count: number) => void
}) {
  const [machineSerial, setMachineSerial] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const raise = async (e: React.FormEvent) => {
    e.preventDefault()
    const serial = machineSerial.trim()
    if (!serial) return
    setBusy(true)
    setError(null)
    try {
      const raised = await api.raiseKit(kit.id, serial)
      onRaised(serial, raised.length)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not raise that kit.')
      setBusy(false)
    }
  }

  const short = kit.lines.filter((l) => !l.covered)

  return (
    <div className="ord__record">
      <button type="button" className="ord__btn ord__btn--ghost ord__back" onClick={onBack}>
        <IconBack />
        Service kits
      </button>

      <header className="ord__record-head">
        <div className="ord__record-ident">
          <span className="ord__partno">{kit.code}</span>
          <h2 className="ord__record-title">{kit.name}</h2>
          <p className="ord__record-desc">{kit.description}</p>
          <div className="ord__chips">
            <span className={`ord__avail is-${kit.ready ? 'in' : 'limited'}`}>
              <span className="ord__avail-dot" aria-hidden />
              {kit.ready ? 'Every part on the shelf' : `${short.length} short`}
            </span>
            {kit.interval_hours !== null && (
              <span className="ord__chip">Every {kit.interval_hours.toLocaleString()} hours</span>
            )}
            <span className="ord__chip">Ready in {kit.longest_lead_days} days at worst</span>
          </div>
        </div>
      </header>

      {/* Said before the button, not after it. Somebody committing a service
          date needs to know which line is the problem while they can still
          move the date. */}
      {short.length > 0 && (
        <p className="ord__note">
          {short.map((l) => l.part.name).join(', ')}{' '}
          {short.length === 1 ? 'cannot be covered' : 'cannot be covered'} from stock today.
          The kit can still be raised — ordering ahead is exactly what a short line calls for —
          but the service will not be complete until it arrives.
        </p>
      )}

      <div className="ord__card ord__card--table">
        <table className="ord__table">
          <thead>
            <tr>
              <th aria-label="Image" />
              <th>Part</th>
              <th>Part number</th>
              <th>Qty</th>
              <th>Lead time</th>
              <th>On hand</th>
            </tr>
          </thead>
          <tbody>
            {kit.lines.map((line) => {
              const thumb = thumbnailFor(line.part.id)
              return (
                <tr key={line.part.id} className="is-static">
                  <td className="ord__td-thumb">
                    <span className="ord__thumb ord__thumb--row">
                      {thumb ? <img src={thumb} alt="" loading="lazy" /> : null}
                    </span>
                  </td>
                  <td>
                    <span className="ord__cell-main">{line.part.name}</span>
                    <span className="ord__cell-sub">{line.part.category}</span>
                  </td>
                  <td className="ord__td-partno">{line.part.part_number}</td>
                  <td className="ord__td-lead">{line.quantity}</td>
                  <td className="ord__td-lead">
                    {line.lead_time_days} <span className="ord__unit">days</span>
                  </td>
                  <td className="ord__td-stock">
                    {line.stock ? (
                      <span className={`ord__stock is-${line.covered ? 'in' : 'out'}`}>
                        <span className="ord__stock-qty">{line.stock.qty_on_hand}</span>
                        <span className="ord__stock-where">{line.stock.warehouse}</span>
                      </span>
                    ) : (
                      <span className="ord__muted-cell">Not stocked</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <form className="ord__kit-raise" onSubmit={raise}>
        <label className="ord__field">
          <span>Machine serial</span>
          <input
            type="text"
            value={machineSerial}
            placeholder="e.g. ZX350LC-7-0042"
            onChange={(e) => setMachineSerial(e.target.value)}
            maxLength={64}
            required
          />
        </label>
        <p className="ord__kit-raise-note">
          Raises {kit.line_count} {kit.line_count === 1 ? 'requirement' : 'requirements'} — one
          per part, each following the ordinary seven stages.
        </p>
        {error && <p className="ord__error">{error}</p>}
        <button type="submit" className="ord__btn" disabled={busy || !machineSerial.trim()}>
          <IconCart />
          {busy ? 'Raising…' : `Raise this service`}
        </button>
      </form>

      <p className="ord__kit-fits-line">Fits {kit.machines.join(', ')}</p>
    </div>
  )
}
