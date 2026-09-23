import { useState } from 'react'
import type { FulfilmentOption, SelectOptionResponse } from '../types/api'

interface FulfilmentOptionSelectorProps {
  requestId: string
  options: FulfilmentOption[]
  currentStatus: string
  onStatusChange?: (newStatus: string) => void
  onSelectedOptionChange?: (option: FulfilmentOption | null) => void
}

export default function FulfilmentOptionSelector({
  requestId,
  options,
  currentStatus,
  onStatusChange,
  onSelectedOptionChange,
}: FulfilmentOptionSelectorProps) {
  const [selectedOptionId, setSelectedOptionId] = useState<string>(
    options.find((o) => o.is_selected)?.id || ''
  )
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>(currentStatus)

  const handleSelectOption = async (optionId: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/fulfilment-requests/${requestId}/select-option`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
        body: JSON.stringify({ optionId }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.error?.message || 'Failed to select fulfilment option.')
      }

      const data: SelectOptionResponse = await res.json()
      setSelectedOptionId(optionId)
      setStatus(data.status)
      onStatusChange?.(data.status)
      onSelectedOptionChange?.(options.find((o) => o.id === optionId) || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const handleProceedToAllocation = async () => {
    if (!selectedOptionId) {
      setError('Please choose a fulfilment option first.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/fulfilment-requests/${requestId}/proceed-to-allocation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.error?.message || 'Failed to proceed to allocation.')
      }

      const data: SelectOptionResponse = await res.json()
      setStatus(data.status)
      onStatusChange?.(data.status)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const confidenceTone = (confidence: string) => {
    switch (confidence) {
      case 'CONFIRMED':
        return 'fulfil-tag--confirmed'
      case 'PARTIAL':
        return 'fulfil-tag--partial'
      case 'UNCONFIRMED':
      default:
        return 'fulfil-tag--unconfirmed'
    }
  }

  return (
    <div className="fulfil-panel">
      <div className="fulfil-panel__head">
        <div>
          <h4>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Fulfilment Options
          </h4>
          <p className="fulfil-panel__stage">
            Stage: <span>{status}</span>
          </p>
        </div>
        <span className="fulfil-panel__count">
          {options.length} {options.length === 1 ? 'Option' : 'Options'} Available
        </span>
      </div>

      {error && <div className="avail-alert avail-alert--error">⚠️ {error}</div>}

      {status === 'ALLOCATION_PENDING' && (
        <div className="fulfil-confirmed">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <div>
            <strong>Fulfilment Option Confirmed!</strong> Request has reached{' '}
            <span className="fulfil-confirmed__code">ALLOCATION_PENDING</span>.
            Ready to allocate stock.
          </div>
        </div>
      )}

      <div className="fulfil-options">
        {options.map((opt) => {
          const isChosen = selectedOptionId === opt.id
          const locked = status === 'ALLOCATION_PENDING'
          return (
            <div
              key={opt.id}
              onClick={() => !locked && handleSelectOption(opt.id)}
              className={`fulfil-option${isChosen ? ' is-chosen' : ''}${locked ? ' is-locked' : ''}`}
            >
              <div className="fulfil-option__main">
                <input
                  type="radio"
                  name="fulfilment_option"
                  checked={isChosen}
                  onChange={() => handleSelectOption(opt.id)}
                  disabled={locked}
                />
                <div>
                  <div className="fulfil-option__title">
                    <span className="fulfil-option__source">{opt.source_id}</span>
                    <span className="fulfil-option__type">({opt.source_type})</span>
                    <span className={`fulfil-tag ${confidenceTone(opt.confidence)}`}>{opt.confidence}</span>
                    {opt.is_split && <span className="fulfil-tag fulfil-tag--split">Split Fulfilment</span>}
                    {opt.synthetic && <span className="gi-synthetic-tag">SYNTHETIC DEMO DATA</span>}
                  </div>
                  <div className="fulfil-option__details">
                    {opt.transport_data_status === 'CONFIRMED' ? (
                      <>
                        <span>Mode: <strong>{opt.transport_mode}</strong> ({opt.carrier_code})</span>
                        <span>Transit: <strong>{opt.transit_days} {opt.transit_days === 1 ? 'day' : 'days'}</strong></span>
                        {opt.eta && <span>ETA: <strong>{new Date(opt.eta).toLocaleDateString('en-GB')}</strong></span>}
                      </>
                    ) : (
                      <span>Carrier, transit time and ETA: <strong>not connected</strong> (no HCME carrier data)</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="fulfil-option__aside">
                <div className="fulfil-option__cost">
                  <span>Est. Transport Cost</span>
                  <strong>{opt.transport_cost != null ? `€${opt.transport_cost.toFixed(2)}` : 'Not connected'}</strong>
                </div>
                {!locked && (
                  <button
                    type="button"
                    disabled={loading}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectOption(opt.id)
                    }}
                    className={`avail-btn avail-btn--small${isChosen ? ' is-chosen' : ''}`}
                  >
                    {isChosen ? 'Selected' : 'Select'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {status === 'OPTION_SELECTED' && (
        <div className="fulfil-proceed">
          <button
            type="button"
            disabled={loading || !selectedOptionId}
            onClick={handleProceedToAllocation}
            className="avail-btn avail-btn--confirm"
          >
            {loading ? (
              'Advancing...'
            ) : (
              <>
                Confirm &amp; Proceed to Allocation
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
