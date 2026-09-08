import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { Part, RequirementDetail } from '../types'

interface Props {
  onCreated: (req: RequirementDetail) => void
  onCancel: () => void
  /** Preselected when the form is opened from a part record, so "raise a
   *  requirement for THIS part" does not make the reader find it again. */
  initialPartId?: string
}

/**
 * Raising a requirement AND identifying the part, in one form — the backend
 * treats these as one action too (see the docstring on Requirement in
 * app/models.py): picking a specific cataloged part here is what
 * "identification" means, so there is no separate step asking the reader to
 * do it again.
 */
export function NewRequirementForm({ onCreated, onCancel, initialPartId }: Props) {
  const [parts, setParts] = useState<Part[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [partId, setPartId] = useState(initialPartId ?? '')
  const [machineSerial, setMachineSerial] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [reason, setReason] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listParts()
      .then((list) => {
        if (cancelled) return
        setParts(list)
        setPartId((prev) => prev || list[0]?.id || '')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(err instanceof ApiError ? err.message : 'Could not load the parts catalogue.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!partId || !machineSerial.trim() || !reason.trim() || quantity < 1) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const req = await api.createRequirement({
        machine_serial: machineSerial.trim(),
        part_id: partId,
        quantity,
        reason: reason.trim(),
      })
      onCreated(req)
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Could not raise the requirement.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loadError) {
    return <p className="ord__error">{loadError}</p>
  }

  return (
    <form className="ord__form" onSubmit={handleSubmit}>
      <h2 className="ord__form-title">Raise a parts requirement</h2>

      <label className="ord__field">
        <span>Part</span>
        <select
          value={partId}
          onChange={(e) => setPartId(e.target.value)}
          disabled={!parts}
          required
        >
          {!parts && <option>Loading…</option>}
          {parts?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} — {p.category}
            </option>
          ))}
        </select>
      </label>

      <label className="ord__field">
        <span>Machine serial</span>
        <input
          type="text"
          placeholder="e.g. ZX350-4521"
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

      <label className="ord__field">
        <span>Reason</span>
        <textarea
          placeholder="e.g. Bearing failure found on inspection"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={500}
          rows={3}
          required
        />
      </label>

      {submitError && <p className="ord__error">{submitError}</p>}

      <div className="ord__form-actions">
        <button type="button" className="ord__btn ord__btn--ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="ord__btn" disabled={submitting || !parts}>
          {submitting ? 'Raising…' : 'Raise requirement'}
        </button>
      </div>
    </form>
  )
}
