import { useState } from 'react'
import { api, ApiError } from '../api'
import { STAGE_LABELS } from '../types'
import type { RequirementDetail as Detail, Stage } from '../types'
import { StageTracker } from './StageTracker'

interface Props {
  requirement: Detail
  onChanged: (req: Detail) => void
  onBack: () => void
}

/**
 * One action, never a menu of them.
 *
 * Which action is possible is the backend's decision, not this component's:
 * it reports `next_stage`, and that maps to exactly one button. The state
 * machine's rules live in services/workflow.py and are not restated here, so
 * the two cannot drift into disagreeing about what is allowed.
 */
const ACTION_LABELS: Readonly<Record<Stage, string>> = {
  requirement_raised: 'Raise requirement',
  identified: 'Identify part',
  availability_checked: 'Check availability',
  ordered: 'Place order',
  inventory_allocated: 'Allocate stock',
  shipped: 'Mark shipped',
  received: 'Confirm goods receipt',
}

export function RequirementDetail({ requirement, onChanged, onBack }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [supplier, setSupplier] = useState('')
  const [carrier, setCarrier] = useState('')

  const next = requirement.next_stage

  const run = async (fn: () => Promise<Detail>) => {
    setBusy(true)
    setError(null)
    try {
      onChanged(await fn())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'That action failed.')
    } finally {
      setBusy(false)
    }
  }

  const act = () => {
    if (!next) return
    const id = requirement.id
    if (next === 'availability_checked') return run(() => api.checkAvailability(id))
    if (next === 'ordered') return run(() => api.order(id, supplier))
    if (next === 'inventory_allocated') return run(() => api.allocate(id))
    if (next === 'shipped') return run(() => api.ship(id, carrier))
    if (next === 'received') return run(() => api.receive(id))
    return undefined
  }

  return (
    <div className="ord__detail">
      <button type="button" className="ord__btn ord__btn--ghost ord__back" onClick={onBack}>
        ← All requirements
      </button>

      <header className="ord__detail-head">
        <div>
          <h2 className="ord__detail-title">
            #{requirement.id} · {requirement.part.name}
          </h2>
          <p className="ord__detail-sub">
            {requirement.quantity} × {requirement.part.category} · machine{' '}
            {requirement.machine_serial}
          </p>
          <p className="ord__detail-reason">{requirement.reason}</p>
        </div>
        <span className={`ord__stage-pill is-${requirement.stage}`}>
          {STAGE_LABELS[requirement.stage]}
        </span>
      </header>

      {requirement.available_at_check === false && (
        <p className="ord__note">
          Not enough on hand when availability was checked — this one is on backorder, and
          stock cannot be allocated until it arrives.
        </p>
      )}

      <StageTracker stage={requirement.stage} events={requirement.events} />

      {error && <p className="ord__error">{error}</p>}

      {next ? (
        <div className="ord__action">
          {next === 'ordered' && (
            <label className="ord__field ord__field--inline">
              <span>Supplier (optional)</span>
              <input
                type="text"
                value={supplier}
                placeholder="e.g. Hitachi Parts EU"
                onChange={(e) => setSupplier(e.target.value)}
                maxLength={120}
              />
            </label>
          )}
          {next === 'shipped' && (
            <label className="ord__field ord__field--inline">
              <span>Carrier (optional)</span>
              <input
                type="text"
                value={carrier}
                placeholder="e.g. DHL"
                onChange={(e) => setCarrier(e.target.value)}
                maxLength={120}
              />
            </label>
          )}
          <button type="button" className="ord__btn" onClick={act} disabled={busy}>
            {busy ? 'Working…' : ACTION_LABELS[next]}
          </button>
        </div>
      ) : (
        <p className="ord__done">
          Received. Arrival confirmed against what was sent — this requirement is closed.
        </p>
      )}
    </div>
  )
}
