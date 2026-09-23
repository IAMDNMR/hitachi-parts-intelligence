import { useEffect, useMemo, useState, type FormEvent } from 'react'
import type {
  ApiErrorBody,
  AvailabilityResponse,
  AvailabilitySource,
  FulfilmentOption,
  FulfilmentOptionsResponse,
  FulfilmentRequest,
  Part,
} from '../types/api'

/** A real HCME Europe dealer branch from GET /api/v1/dealers. */
interface DealerOption {
  dealer_id: string
  dealer_name: string
  city: string | null
  country: string
}
import FulfilmentOptionSelector from './FulfilmentOptionSelector'
import AllocationOrderPanel from './AllocationOrderPanel'

interface AvailabilityCheckerProps {
  part: Part
  defaultQty?: number
}

/** Local convenience only (per-viewer, never a source of truth) — the real
 *  requester identity is persisted on the FulfilmentRequest/Customer nodes
 *  in Neo4j, not read back from here. */
const REQUESTER_KEY = 'hcme-requester-identity'

export default function AvailabilityChecker({ part, defaultQty = 1 }: AvailabilityCheckerProps) {
  const [quantity, setQuantity] = useState(defaultQty)
  const [destinationBranch, setDestinationBranch] = useState('')
  const [requesterName, setRequesterName] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(REQUESTER_KEY) || '{}').name || ''
    } catch {
      return ''
    }
  })
  const [requesterEmail, setRequesterEmail] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(REQUESTER_KEY) || '{}').email || ''
    } catch {
      return ''
    }
  })
  const [dealers, setDealers] = useState<DealerOption[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [results, setResults] = useState<AvailabilitySource[] | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const [requestStatus, setRequestStatus] = useState<string>('REQUESTED')
  const [fulfilmentOptions, setFulfilmentOptions] = useState<FulfilmentOption[] | null>(null)
  const [selectedOption, setSelectedOption] = useState<FulfilmentOption | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/dealers')
      .then((res) => (res.ok ? res.json() : []))
      .then((rows: DealerOption[]) => !cancelled && setDealers(rows))
      .catch(() => !cancelled && setDealers([]))
    return () => {
      cancelled = true
    }
  }, [])

  const dealersByCountry = useMemo(() => {
    const groups = new Map<string, DealerOption[]>()
    for (const d of dealers) groups.set(d.country, [...(groups.get(d.country) ?? []), d])
    return [...groups.entries()]
  }, [dealers])

  const handleCheckAvailability = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setFulfilmentOptions(null)

    try {
      localStorage.setItem(REQUESTER_KEY, JSON.stringify({ name: requesterName, email: requesterEmail }))
    } catch {
      // localStorage unavailable — the request still carries the identity to the API.
    }

    try {
      // 1. Create Fulfilment Request — persists the requester (Customer node,
      // via [:REQUESTED]) alongside the request itself, not just in React state.
      const createRes = await fetch('/api/v1/fulfilment-requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
        body: JSON.stringify({
          partNumber: part.partNumber || part.id || 'PT-GENERIC',
          quantity: Number(quantity),
          destinationBranchId: destinationBranch,
          machineContext: part.machine || null,
          requesterName: requesterName.trim() || null,
          requesterEmail: requesterEmail.trim() || null,
        }),
      })

      if (!createRes.ok) {
        const errData: ApiErrorBody = await createRes.json()
        throw new Error(errData.error?.message || 'Failed to create availability request.')
      }

      const requestData: FulfilmentRequest = await createRes.json()
      setRequestId(requestData.id)

      // 2. Trigger Availability Check
      const availRes = await fetch(`/api/v1/fulfilment-requests/${requestData.id}/availability`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
        body: JSON.stringify({
          partNumber: part.partNumber || part.id || 'PT-GENERIC',
          quantity: Number(quantity),
          destinationBranchId: destinationBranch,
        }),
      })

      if (!availRes.ok) {
        const errData: ApiErrorBody = await availRes.json()
        throw new Error(errData.error?.message || 'Availability check failed.')
      }

      const availData: AvailabilityResponse = await availRes.json()
      setResults(availData.availabilityResults || [])
      setRequestStatus('AVAILABILITY_CHECKED')

      // 3. Automatically compute candidate Fulfilment Options (Phase 5)
      setLoadingOptions(true)
      const optionsRes = await fetch(`/api/v1/fulfilment-requests/${requestData.id}/options`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
      })

      if (optionsRes.ok) {
        const optionsData: FulfilmentOptionsResponse = await optionsRes.json()
        setFulfilmentOptions(optionsData.options || [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
      setLoadingOptions(false)
    }
  }

  const badgeTone = (status: string | undefined, isStale: boolean | undefined) => {
    if (isStale) return 'avail-tag--stale'
    switch (status) {
      case 'AVAILABLE':
        return 'avail-tag--available'
      case 'UNAVAILABLE':
        return 'avail-tag--unavailable'
      case 'UNKNOWN':
      default:
        return 'avail-tag--unknown'
    }
  }

  return (
    <div className="avail-panel">
      <div className="avail-panel__head">
        <h4>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Check Stock Availability
        </h4>
      </div>

      <form onSubmit={handleCheckAvailability} className="avail-form">
        <div className="avail-field">
          <label>Your name</label>
          <input
            type="text"
            value={requesterName}
            onChange={(e) => setRequesterName(e.target.value)}
            placeholder="Requester name"
            required
          />
        </div>

        <div className="avail-field">
          <label>Your email</label>
          <input
            type="email"
            value={requesterEmail}
            onChange={(e) => setRequesterEmail(e.target.value)}
            placeholder="requester@company.com"
            required
          />
        </div>

        <div className="avail-field">
          <label>Required Quantity</label>
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            required
          />
        </div>

        <div className="avail-field">
          <label>Destination Dealer</label>
          <select value={destinationBranch} onChange={(e) => setDestinationBranch(e.target.value)} required>
            <option value="" disabled>
              {dealers.length ? 'Choose a Hitachi dealer…' : 'Loading dealers…'}
            </option>
            {dealersByCountry.map(([country, rows]) => (
              <optgroup key={country} label={country}>
                {rows.map((d) => (
                  <option key={d.dealer_id} value={d.dealer_id}>
                    {d.dealer_name}{d.city ? ` — ${d.city}` : ''}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <div className="avail-field avail-field--submit">
          <button type="submit" disabled={loading} className="avail-btn avail-btn--primary">
            {loading ? (
              <>
                <svg className="avail-spinner" width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle opacity="0.25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path opacity="0.75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Querying Sources...
              </>
            ) : (
              'Check Stock'
            )}
          </button>
        </div>
      </form>

      {error && <div className="avail-alert avail-alert--error">⚠️ {error}</div>}

      {results && (
        <div className="avail-results">
          <h5>Stock by location</h5>
          <div className="avail-results__list">
            {results.map((res) => (
              <div className="avail-result" key={res.source_id}>
                <div>
                  <div className="avail-result__name">
                    <span>{res.source_name || res.source_id}</span>
                    <span className="avail-result__meta">({res.source_type})</span>
                    {res.provenance === 'SYNTHETIC_DEMO' && (
                      <span className="gi-synthetic-tag" title="Not real HCME stock — no live HCME inventory feed is connected">
                        SYNTHETIC DEMO DATA
                      </span>
                    )}
                  </div>
                  <div className="avail-result__provider">
                    As of: {new Date(res.inventory_timestamp).toLocaleTimeString('en-GB')}
                  </div>
                </div>

                <div className="avail-result__status">
                  <div className="avail-result__qty">
                    {res.status === 'UNKNOWN' ? (
                      <span className="avail-result__unconfirmed">Data unconfirmed</span>
                    ) : (
                      <span className="avail-result__available">{res.available_qty} units available</span>
                    )}
                  </div>
                  <span className={`avail-tag ${badgeTone(res.status, res.is_stale)}`}>
                    {res.is_stale ? 'STALE DATA' : (res.status === 'UNKNOWN' ? 'UNCONFIRMED' : res.status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loadingOptions && (
        <div className="avail-loading-note">Calculating candidate transport routes and options...</div>
      )}

      {fulfilmentOptions && fulfilmentOptions.length > 0 && requestId && (
        <FulfilmentOptionSelector
          requestId={requestId}
          options={fulfilmentOptions}
          currentStatus={requestStatus}
          onStatusChange={(newStatus) => setRequestStatus(newStatus)}
          onSelectedOptionChange={(opt) => setSelectedOption(opt)}
        />
      )}

      {requestStatus === 'ALLOCATION_PENDING' && requestId && (
        <AllocationOrderPanel
          requestId={requestId}
          partNumber={part.partNumber ?? ''}
          quantity={quantity}
          sourceId={selectedOption?.source_id ?? 'UNKNOWN'}
        />
      )}
    </div>
  )
}
