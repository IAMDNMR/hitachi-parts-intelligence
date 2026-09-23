import { useState, useEffect } from 'react'
import type {
  AvailabilitySource,
  CartItem,
  DealerOption,
  FulfilmentOption,
  FulfilmentOptionsResponse,
  FulfilmentRequest,
  TransportComparisonResponse,
} from '../../types/api'
import Stage1Cart from './Stage1Cart'
import Stage2Requester from './Stage2Requester'
import Stage3DestinationDealer from './Stage3DestinationDealer'
import Stage4Availability from './Stage4Availability'
import Stage5Transportation, { type UnifiedTransportOption } from './Stage5Transportation'
import Stage6OrderReview from './Stage6OrderReview'
import Stage7PostOrder from './Stage7PostOrder'
import './CheckoutWizard.css'

interface CheckoutWizardProps {
  item: CartItem
  onClose: () => void
  onComplete: () => void
}

const REQUESTER_KEY = 'hcme-requester-identity'

const STAGE_NAMES = [
  'Cart Item',
  'Requester',
  'Destination Dealer',
  'Stock Availability',
  'Transportation',
  'Order Review',
  'Lifecycle & Service',
]

export default function CheckoutWizard({ item: initialItem, onClose, onComplete }: CheckoutWizardProps) {
  const [currentStage, setCurrentStage] = useState<number>(1)
  const [item, setItem] = useState<CartItem>(initialItem)

  // Requester identity state
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
  const [requesterCompany, setRequesterCompany] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(REQUESTER_KEY) || '{}').company || ''
    } catch {
      return ''
    }
  })

  // European dealers
  const [dealers, setDealers] = useState<DealerOption[]>([])
  const [selectedDealerId, setSelectedDealerId] = useState<string>('')
  const [selectedDealer, setSelectedDealer] = useState<DealerOption | null>(null)

  // Availability & Fulfilment Request
  const [requestId, setRequestId] = useState<string | null>(null)
  const [lastCheckedBranchId, setLastCheckedBranchId] = useState<string | null>(null)
  const [lastCheckedQty, setLastCheckedQty] = useState<number | null>(null)
  const [availLoading, setAvailLoading] = useState<boolean>(false)
  const [availError, setAvailError] = useState<string | null>(null)
  const [availSources, setAvailSources] = useState<AvailabilitySource[] | null>(null)

  // Transport & Options
  const [fulfilmentOptions, setFulfilmentOptions] = useState<FulfilmentOption[] | null>(null)
  const [transportComparison, setTransportComparison] = useState<TransportComparisonResponse | null>(null)
  const [transportLoading, setTransportLoading] = useState<boolean>(false)
  const [transportError, setTransportError] = useState<string | null>(null)
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null)
  const [selectedOption, setSelectedOption] = useState<UnifiedTransportOption | null>(null)

  // Review & Confirmation
  const [orderSubmitting, setOrderSubmitting] = useState<boolean>(false)
  const [orderError, setOrderError] = useState<string | null>(null)

  // Fetch real European dealer network on mount
  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/dealers')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: DealerOption[]) => {
        if (!cancelled) {
          setDealers(data)
          // Default selection to first dealer if none selected
          const firstDealer = data[0]
          if (firstDealer && !selectedDealerId) {
            setSelectedDealerId(firstDealer.dealer_id)
            setSelectedDealer(firstDealer)
          }
        }
      })
      .catch(() => {
        if (!cancelled) setDealers([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Persist identity changes
  const saveIdentity = () => {
    try {
      localStorage.setItem(
        REQUESTER_KEY,
        JSON.stringify({ name: requesterName, email: requesterEmail, company: requesterCompany })
      )
    } catch {
      // localStorage unavailable
    }
  }

  // Trigger Availability and create request if needed
  const performStockCheck = async () => {
    setAvailLoading(true)
    setAvailError(null)
    saveIdentity()

    try {
      const partNum = item.partNumber || item.id || '4663907'
      let curReqId = requestId

      // Create new request if not yet created or destination/qty changed
      if (!curReqId || lastCheckedBranchId !== selectedDealerId || lastCheckedQty !== item.qty) {
        const createRes = await fetch('/api/v1/fulfilment-requests', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-test-user-id': 'site-visitor-demo',
            'x-test-role': 'CUSTOMER',
          },
          body: JSON.stringify({
            partNumber: partNum,
            quantity: Number(item.qty),
            destinationBranchId: selectedDealerId,
            machineContext: item.machine || null,
            requesterName: requesterName.trim() || null,
            requesterEmail: requesterEmail.trim() || null,
          }),
        })

        if (!createRes.ok) {
          const errData = await createRes.json()
          throw new Error(errData.error?.message || 'Failed to create fulfilment request.')
        }

        const reqData: FulfilmentRequest = await createRes.json()
        curReqId = reqData.id
        setRequestId(reqData.id)
        setLastCheckedBranchId(selectedDealerId)
        setLastCheckedQty(item.qty)
      }

      // 2. Query Availability
      const availRes = await fetch(`/api/v1/fulfilment-requests/${curReqId}/availability`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
        body: JSON.stringify({
          partNumber: partNum,
          quantity: Number(item.qty),
          destinationBranchId: selectedDealerId,
        }),
      })

      if (!availRes.ok) {
        const errData = await availRes.json()
        throw new Error(errData.error?.message || 'Availability check failed.')
      }

      const availData = await availRes.json()
      setAvailSources(availData.availabilityResults || [])

      // 3. Preload candidate Fulfilment Options & Transport Options
      fetchCandidateOptions(curReqId)

      // Advance to Stage 4
      setCurrentStage(4)
    } catch (err) {
      setAvailError(err instanceof Error ? err.message : String(err))
    } finally {
      setAvailLoading(false)
    }
  }

  // Pre-load transport & candidate fulfilment options
  const fetchCandidateOptions = async (reqId: string) => {
    setTransportLoading(true)
    setTransportError(null)

    try {
      // 1. Generate options in Neo4j
      const optRes = await fetch(`/api/v1/fulfilment-requests/${reqId}/options`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
      })

      if (optRes.ok) {
        const optData: FulfilmentOptionsResponse = await optRes.json()
        setFulfilmentOptions(optData.options || [])
        const first = optData.options?.[0]
        if (first && !selectedOptionId) {
          setSelectedOptionId(first.id)
        }
      }

      // 2. Fetch full transport comparison
      const transRes = await fetch(`/api/v1/fulfilment-requests/${reqId}/transport-options`)
      if (transRes.ok) {
        const transData: TransportComparisonResponse = await transRes.json()
        setTransportComparison(transData)
      }
    } catch (err) {
      setTransportError(err instanceof Error ? err.message : String(err))
    } finally {
      setTransportLoading(false)
    }
  }

  // Advance from Transportation to Review
  const handleProceedToReview = async () => {
    if (!requestId || !selectedOptionId) {
      setCurrentStage(6)
      return
    }

    try {
      // Select option in Neo4j
      await fetch(`/api/v1/fulfilment-requests/${requestId}/select-option`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
        body: JSON.stringify({ optionId: selectedOptionId }),
      })

      // Proceed to allocation pending
      await fetch(`/api/v1/fulfilment-requests/${requestId}/proceed-to-allocation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-test-user-id': 'site-visitor-demo',
          'x-test-role': 'CUSTOMER',
        },
      })
    } catch {
      // Proceed even if state transition already applied
    }

    setCurrentStage(6)
  }

  // Authorize and advance to Stage 7
  const handleConfirmOrder = () => {
    setOrderSubmitting(true)
    setOrderError(null)
    setTimeout(() => {
      setOrderSubmitting(false)
      setCurrentStage(7)
    }, 400)
  }

  return (
    <div className="cw-modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="cw-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cw-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="cw-header">
          <div className="cw-header__left">
            <button
              type="button"
              className="cw-header__back-btn"
              onClick={onClose}
              aria-label="Back to Cart"
            >
              ← Back to Cart
            </button>
            <div className="cw-header__main">
              <span className="cw-header__eyebrow">HCME AFTER-SALES · PARTS FULFILMENT</span>
              <h2 id="cw-title" className="cw-header__title">
                European Fulfilment Journey
              </h2>
            </div>
          </div>
          <button type="button" className="cw-close-btn" onClick={onClose} aria-label="Close dialog">
            ×
          </button>
        </div>

        {/* Global 7-Stage Horizontal Stepper */}
        <nav className="cw-stepper" aria-label="Fulfilment Journey Stages">
          {STAGE_NAMES.map((name, idx) => {
            const stepNum = idx + 1
            const isCompleted = currentStage > stepNum
            const isActive = currentStage === stepNum
            return (
              <div
                key={name}
                className={`cw-step${isActive ? ' is-active' : ''}${isCompleted ? ' is-completed' : ''}`}
                title={`Stage ${stepNum}: ${name}`}
              >
                <div className="cw-step__indicator">
                  {isCompleted ? (
                    <span className="cw-step__check">✓</span>
                  ) : (
                    <span className="cw-step__num">{stepNum}</span>
                  )}
                </div>
                <span className="cw-step__label">{name}</span>
                {idx < STAGE_NAMES.length - 1 && <span className="cw-step__connector" />}
              </div>
            )
          })}
        </nav>

        {/* Active Stage View — ONE STAGE AT A TIME */}
        <div className="cw-body">
          {currentStage === 1 && (
            <Stage1Cart
              item={item}
              onUpdateQty={(q) => setItem((prev) => ({ ...prev, qty: q }))}
              onNext={() => setCurrentStage(2)}
              onClose={onClose}
            />
          )}

          {currentStage === 2 && (
            <Stage2Requester
              name={requesterName}
              email={requesterEmail}
              company={requesterCompany}
              onChangeName={setRequesterName}
              onChangeEmail={setRequesterEmail}
              onChangeCompany={setRequesterCompany}
              onBack={() => setCurrentStage(1)}
              onNext={() => {
                saveIdentity()
                setCurrentStage(3)
              }}
            />
          )}

          {currentStage === 3 && (
            <Stage3DestinationDealer
              dealers={dealers}
              selectedDealerId={selectedDealerId}
              onSelectDealer={(d) => {
                setSelectedDealerId(d.dealer_id)
                setSelectedDealer(d)
              }}
              onBack={() => setCurrentStage(2)}
              onNext={performStockCheck}
            />
          )}

          {currentStage === 4 && (
            <Stage4Availability
              loading={availLoading}
              error={availError}
              sources={availSources}
              requiredQty={item.qty}
              partNumber={item.partNumber || item.id}
              onRetry={performStockCheck}
              onBack={() => setCurrentStage(3)}
              onNext={() => {
                if (requestId && (!fulfilmentOptions || fulfilmentOptions.length === 0)) {
                  fetchCandidateOptions(requestId)
                }
                setCurrentStage(5)
              }}
            />
          )}

          {currentStage === 5 && (
            <Stage5Transportation
              loading={transportLoading}
              error={transportError}
              transportComparison={transportComparison}
              fulfilmentOptions={fulfilmentOptions}
              selectedOptionId={selectedOptionId}
              onSelectOption={(opt) => {
                setSelectedOptionId(opt.id)
                setSelectedOption(opt)
              }}
              onBack={() => setCurrentStage(4)}
              onNext={handleProceedToReview}
            />
          )}

          {currentStage === 6 && (
            <Stage6OrderReview
              item={item}
              requesterName={requesterName}
              requesterEmail={requesterEmail}
              requesterCompany={requesterCompany}
              dealer={selectedDealer}
              transportComparison={transportComparison}
              selectedOption={selectedOption}
              onBack={() => setCurrentStage(5)}
              onConfirmOrder={handleConfirmOrder}
              submitting={orderSubmitting}
              error={orderError}
            />
          )}

          {currentStage === 7 && requestId && (
            <Stage7PostOrder
              requestId={requestId}
              partNumber={item.partNumber || item.id}
              quantity={item.qty}
              sourceId="DEPOT-OOSTERHOUT"
              dealerId={selectedDealerId}
              dealerName={selectedDealer?.dealer_name}
              onFinishJourney={() => {
                onComplete()
                onClose()
              }}
            />
          )}
        </div>

        {/* Global 4-Tier Provenance Footer */}
        <footer className="cw-footer">
          <div className="cw-footer__provenance">
            <span className="cw-prov-item">
              <strong className="cw-tag cw-tag--real">REAL</strong> Parts, Machines, Dealer Branches &amp; Coordinates
            </span>
            <span className="cw-prov-item">
              <strong className="cw-tag cw-tag--derived">DERIVED</strong> Haversine Straight-Line Distance &amp; Bands
            </span>
            <span className="cw-prov-item">
              <strong className="cw-tag cw-tag--synthetic">SYNTHETIC_DEMO</strong> Stock, Transport Rates, Transit,
              Tracking &amp; Service
            </span>
            <span className="cw-prov-item">
              <strong className="cw-tag cw-tag--disconnected">NOT_CONNECTED</strong> SAP ERP &amp; Carrier TMS
            </span>
          </div>
        </footer>
      </div>
    </div>
  )
}
