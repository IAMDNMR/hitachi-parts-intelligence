import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../api'
import type { Machine, MachinePart, RequirementDetail } from '../types'

interface Props {
  onCreated: (req: RequirementDetail) => void
  onCancel: () => void
  /** Preselected when the form is opened from a part record, so "raise a
   *  requirement for THIS part" does not make the reader find it again. */
  initialPartId?: string
  /** Preselected when opened from a machine. The machine is chosen FIRST,
   *  because it decides which parts are offered at all. */
  initialMachineId?: string
}

/**
 * Raising a requirement AND identifying the part, in one form — the backend
 * treats these as one action too (see the docstring on Requirement in
 * app/models.py): picking a specific cataloged part here is what
 * "identification" means, so there is no separate step asking the reader to
 * do it again.
 *
 * THE MACHINE COMES FIRST, AND THAT ORDER IS THE FEATURE
 * -----------------------------------------------------
 * This form used to ask for a machine serial as free text, and the database
 * still holds "AXZ120" — not a Hitachi model, matching no fitment record,
 * typed once and never questioned. The machine is now chosen from the fleet,
 * and choosing it decides which parts are offered at all: the list is what
 * the catalogue lists against that machine's own model.
 *
 * The server enforces the same rule independently, so the narrowed list is a
 * courtesy rather than the control — but it means nobody has to discover the
 * rule by being refused.
 */
export function NewRequirementForm({
  onCreated,
  onCancel,
  initialPartId,
  initialMachineId,
}: Props) {
  const [machines, setMachines] = useState<Machine[] | null>(null)
  const [parts, setParts] = useState<MachinePart[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [machineId, setMachineId] = useState(initialMachineId ?? '')
  const [partId, setPartId] = useState(initialPartId ?? '')
  const [quantity, setQuantity] = useState(1)
  const [reason, setReason] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listMachines()
      .then((list) => {
        if (cancelled) return
        setMachines(list)
        setMachineId((prev) => prev || list[0]?.id || '')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(err instanceof ApiError ? err.message : 'Could not load the fleet.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  /* The parts list follows the machine. Changing the machine re-asks the
     question "what fits this one", because the answer is different. */
  useEffect(() => {
    if (!machineId) return undefined
    let cancelled = false
    setParts(null)
    api
      .getMachineParts(machineId)
      .then((list) => {
        if (cancelled) return
        setParts(list)
        /* Keep the preselected part if it still fits; otherwise fall to the
           first one that does, rather than leaving a selection the server
           would refuse. */
        setPartId((prev) =>
          prev && list.some((p) => p.id === prev) ? prev : list[0]?.id || '',
        )
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(
          err instanceof ApiError ? err.message : 'Could not load the parts for that machine.',
        )
      })
    return () => {
      cancelled = true
    }
  }, [machineId])

  const machine = useMemo(
    () => (machines ?? []).find((m) => m.id === machineId) ?? null,
    [machines, machineId],
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!partId || !machineId || !reason.trim() || quantity < 1) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const req = await api.createRequirement({
        machine_id: machineId,
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
        <span>Machine</span>
        <select
          value={machineId}
          onChange={(e) => setMachineId(e.target.value)}
          disabled={!machines}
          required
        >
          {!machines && <option>Loading…</option>}
          {machines?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.serial_number} — {m.model} · {m.customer.name}
            </option>
          ))}
        </select>
      </label>

      <label className="ord__field">
        <span>Part</span>
        <select
          value={partId}
          onChange={(e) => setPartId(e.target.value)}
          disabled={!parts || parts.length === 0}
          required
        >
          {!parts && <option>Loading…</option>}
          {parts?.length === 0 && (
            <option>No part in the catalogue fits this machine</option>
          )}
          {parts?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} — {p.assembly}
            </option>
          ))}
        </select>
      </label>

      {machine && parts && (
        <p className="ord__kit-raise-note">
          Showing the {parts.length} part{parts.length === 1 ? '' : 's'} the catalogue
          lists against a {machine.model}. Anything else is refused rather than
          substituted.
        </p>
      )}

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
        <button
          type="submit"
          className="ord__btn"
          disabled={submitting || !parts || parts.length === 0 || !machineId}
        >
          {submitting ? 'Raising…' : 'Raise requirement'}
        </button>
      </div>
    </form>
  )
}
