import { useState } from 'react'
import type {
  AllocationResult,
  ApiErrorBody,
  OrderResult,
  ServiceJobData,
  ShipmentData,
} from '../../types/api'
import { formatOrderPrice } from '../orderDisplay'
import { simulatedServiceEvent, simulatedShipmentEvent } from '../simulatedEvents'

interface Stage7PostOrderProps {
  requestId: string
  partNumber: string
  quantity: number
  sourceId: string
  dealerId: string
  dealerName?: string
  initialAllocation?: AllocationResult | null
  initialOrder?: OrderResult | null
  onFinishJourney: () => void
}

export default function Stage7PostOrder({
  requestId,
  partNumber,
  quantity,
  sourceId,
  dealerId,
  dealerName,
  initialAllocation = null,
  initialOrder = null,
  onFinishJourney,
}: Stage7PostOrderProps) {
  // Post-order sub-states
  const [allocation, setAllocation] = useState<AllocationResult | null>(initialAllocation)
  const [allocLoading, setAllocLoading] = useState(false)
  const [allocError, setAllocError] = useState<string | null>(null)

  const [order, setOrder] = useState<OrderResult | null>(initialOrder)
  const [orderLoading, setOrderLoading] = useState(false)
  const [orderError, setOrderError] = useState<string | null>(null)

  const [shipment, setShipment] = useState<ShipmentData | null>(null)
  const [shipmentLoading, setShipmentLoading] = useState(false)
  const [shipmentError, setShipmentError] = useState<string | null>(null)

  const [serviceJob, setServiceJob] = useState<ServiceJobData | null>(null)
  const [serviceLoading, setServiceLoading] = useState(false)
  const [serviceError, setServiceError] = useState<string | null>(null)

  const authHeaders = {
    'Content-Type': 'application/json',
    'x-test-user-id': 'site-visitor-demo',
    'x-test-role': 'CUSTOMER',
  }

  // 1. Allocate Inventory
  const handleAllocate = async () => {
    setAllocLoading(true)
    setAllocError(null)
    try {
      const res = await fetch(`/api/v1/fulfilment-requests/${requestId}/allocation`, {
        method: 'POST',
        headers: { ...authHeaders, 'x-idempotency-key': `alloc-${requestId}` },
      })
      const data = await res.json()
      if (!res.ok) {
        const err = data as ApiErrorBody
        throw new Error(err.error?.message || 'Inventory allocation failed.')
      }
      setAllocation(data as AllocationResult)
    } catch (err) {
      setAllocError(err instanceof Error ? err.message : String(err))
    } finally {
      setAllocLoading(false)
    }
  }

  // 2. Place Order
  const handlePlaceOrder = async () => {
    setOrderLoading(true)
    setOrderError(null)
    try {
      const res = await fetch(`/api/v1/fulfilment-requests/${requestId}/order`, {
        method: 'POST',
        headers: { ...authHeaders, 'x-idempotency-key': `order-${requestId}` },
      })
      const data = await res.json()
      if (!res.ok) {
        const err = data as ApiErrorBody
        throw new Error(err.error?.message || 'Order creation failed.')
      }
      setOrder(data as OrderResult)
    } catch (err) {
      setOrderError(err instanceof Error ? err.message : String(err))
    } finally {
      setOrderLoading(false)
    }
  }

  // 3. Create Shipment
  const handleCreateShipment = async () => {
    if (!order) return
    setShipmentLoading(true)
    setShipmentError(null)
    try {
      const res = await fetch('/api/v1/shipments', {
        method: 'POST',
        headers: { ...authHeaders, 'x-idempotency-key': `ship-${order.id}` },
        body: JSON.stringify({ order_id: order.id, service_tier: 'STANDARD' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || data.error?.message || 'Shipment creation failed.')
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  // 4. Dispatch Shipment
  const handleDispatchShipment = async () => {
    if (!shipment) return
    setShipmentLoading(true)
    try {
      const res = await fetch(`/api/v1/shipments/${shipment.shipment_id}/dispatch`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Dispatch failed')
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  // 5. Deliver Shipment
  const handleDeliverShipment = async () => {
    if (!shipment) return
    setShipmentLoading(true)
    try {
      const res = await fetch(`/api/v1/shipments/${shipment.shipment_id}/deliver`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Delivery confirmation failed')
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  // 6. Create Service Job
  const handleCreateServiceJob = async () => {
    if (!order) return
    setServiceLoading(true)
    setServiceError(null)
    try {
      const res = await fetch('/api/v1/service-jobs', {
        method: 'POST',
        headers: { ...authHeaders, 'x-idempotency-key': `srv-${order.id}` },
        body: JSON.stringify({ order_id: order.id, service_type: 'PARTS_INSTALLATION' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Service job creation failed.')
      setServiceJob(data as ServiceJobData)
    } catch (err) {
      setServiceError(err instanceof Error ? err.message : String(err))
    } finally {
      setServiceLoading(false)
    }
  }

  // 7. Service job status transitions
  const handleReceivePart = async () => {
    if (!serviceJob) return
    setServiceLoading(true)
    try {
      const res = await fetch(`/api/v1/service-jobs/${serviceJob.service_job_id}/receive`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Part receipt failed')
      setServiceJob(data as ServiceJobData)
    } catch (err) {
      setServiceError(err instanceof Error ? err.message : String(err))
    } finally {
      setServiceLoading(false)
    }
  }

  const handleStartService = async () => {
    if (!serviceJob) return
    setServiceLoading(true)
    try {
      const res = await fetch(`/api/v1/service-jobs/${serviceJob.service_job_id}/start`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Service start failed')
      setServiceJob(data as ServiceJobData)
    } catch (err) {
      setServiceError(err instanceof Error ? err.message : String(err))
    } finally {
      setServiceLoading(false)
    }
  }

  const handleInstallPart = async () => {
    if (!serviceJob) return
    setServiceLoading(true)
    try {
      const res = await fetch(`/api/v1/service-jobs/${serviceJob.service_job_id}/install`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Installation confirmation failed')
      setServiceJob(data as ServiceJobData)
    } catch (err) {
      setServiceError(err instanceof Error ? err.message : String(err))
    } finally {
      setServiceLoading(false)
    }
  }

  const handleCompleteService = async () => {
    if (!serviceJob) return
    setServiceLoading(true)
    try {
      const res = await fetch(`/api/v1/service-jobs/${serviceJob.service_job_id}/complete`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Service completion failed')
      setServiceJob(data as ServiceJobData)
    } catch (err) {
      setServiceError(err instanceof Error ? err.message : String(err))
    } finally {
      setServiceLoading(false)
    }
  }

  const isClosed = serviceJob?.status === 'COMPLETED'

  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--synthetic">FULFILMENT LIFECYCLE &amp; SERVICE</div>
        <h3 className="cw-stage__title">7. Demonstration: Allocation → Order → Shipment → Service → Close</h3>
        <p className="cw-stage__desc">
          Simulated end-to-end execution using deterministic demonstration data. No live HCME ERP, inventory, carrier,
          TMS or dealer service system is connected.
        </p>
      </div>

      {/* Progress Stepper Bar */}
      <div className="cw-mini-stepper">
        <div className={`cw-mini-step${allocation ? ' is-done' : ' is-active'}`}>
          <span className="cw-mini-step__num">1</span>
          <span className="cw-mini-step__name">Simulated Allocation</span>
        </div>
        <div className={`cw-mini-step${order ? ' is-done' : allocation ? ' is-active' : ''}`}>
          <span className="cw-mini-step__num">2</span>
          <span className="cw-mini-step__name">Simulated Order</span>
        </div>
        <div className={`cw-mini-step${shipment?.status === 'DELIVERED' ? ' is-done' : shipment ? ' is-active' : ''}`}>
          <span className="cw-mini-step__num">3</span>
          <span className="cw-mini-step__name">Simulated Shipment</span>
        </div>
        <div className={`cw-mini-step${serviceJob?.status === 'COMPLETED' ? ' is-done' : serviceJob ? ' is-active' : ''}`}>
          <span className="cw-mini-step__num">4</span>
          <span className="cw-mini-step__name">Simulated Service</span>
        </div>
        <div className={`cw-mini-step${isClosed ? ' is-done' : ''}`}>
          <span className="cw-mini-step__num">5</span>
          <span className="cw-mini-step__name">Demo Completed</span>
        </div>
      </div>

      {/* Milestone 1: Allocation */}
      <div className="cw-milestone-card">
        <div className="cw-milestone-head">
          <div className="cw-milestone-indicator">
            {allocation ? (
              <span className="cw-milestone-dot cw-milestone-dot--done">✓</span>
            ) : (
              <span className="cw-milestone-dot cw-milestone-dot--pending">1</span>
            )}
            <div>
              <h4 className="cw-milestone-title">Milestone 1: Simulated Inventory Allocation</h4>
              <span className="cw-milestone-sub">Demonstrates how inventory would be reserved against the selected fulfilment source</span>
            </div>
          </div>
          {allocation && (
            <span className="cw-status-badge cw-status-badge--success">{allocation.status}</span>
          )}
        </div>

        {allocError && <div className="cw-alert cw-alert--error">⚠️ {allocError}</div>}

        {!allocation && (
          <div className="cw-milestone-body">
            <p>Ready to allocate {quantity} unit(s) of {partNumber} from source {sourceId}.</p>
            <button
              type="button"
              className="cw-btn cw-btn--confirm"
              onClick={handleAllocate}
              disabled={allocLoading}
            >
              {allocLoading ? 'Allocating Inventory...' : 'Allocate Inventory →'}
            </button>
          </div>
        )}

        {allocation && (
          <div className="cw-milestone-info">
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Allocation ID</span>
              <strong className="cw-spec-item__val"><code>{allocation.allocation_id || allocation.id}</code></strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Allocated Quantity</span>
              <strong className="cw-spec-item__val">{allocation.quantity} units</strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Source Node</span>
              <strong className="cw-spec-item__val">{allocation.source_id || allocation.sourceId}</strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Data Source</span>
              <strong className="cw-spec-item__val cw-val--disconnected">DEMO / SIMULATED</strong>
            </div>
          </div>
        )}
      </div>

      {/* Milestone 2: Order Placement */}
      {allocation && (
        <div className="cw-milestone-card">
          <div className="cw-milestone-head">
            <div className="cw-milestone-indicator">
              {order ? (
                <span className="cw-milestone-dot cw-milestone-dot--done">✓</span>
              ) : (
                <span className="cw-milestone-dot cw-milestone-dot--pending">2</span>
              )}
              <div>
                <h4 className="cw-milestone-title">Milestone 2: Simulated Order Creation</h4>
                <span className="cw-milestone-sub">Demonstrates the future sales-order workflow. No live HCME ERP order is created.</span>
              </div>
            </div>
            {order && (
              <span className="cw-status-badge cw-status-badge--success">{order.status}</span>
            )}
          </div>

          {orderError && <div className="cw-alert cw-alert--error">⚠️ {orderError}</div>}

          {!order && (
            <div className="cw-milestone-body">
              <p>Simulated allocation recorded. Create the simulated order record in the demonstration graph (no HCME order is created).</p>
              <button
                type="button"
                className="cw-btn cw-btn--primary"
                onClick={handlePlaceOrder}
                disabled={orderLoading}
              >
                {orderLoading ? 'Creating Simulated Order...' : 'Create Simulated Order →'}
              </button>
            </div>
          )}

          {order && (
            <div className="cw-milestone-info">
              <div className="cw-spec-item">
                <span className="cw-spec-item__label">Order ID</span>
                <strong className="cw-spec-item__val"><code>{order.id}</code></strong>
              </div>
              <div className="cw-spec-item">
                <span className="cw-spec-item__label">Part Commercial Price</span>
                <strong className="cw-spec-item__val">{formatOrderPrice(order)}</strong>
              </div>
              <div className="cw-spec-item">
                <span className="cw-spec-item__label">Data Source</span>
                <strong className="cw-spec-item__val cw-val--disconnected">DEMO / SIMULATED</strong>
              </div>
              <div className="cw-spec-item">
                <span className="cw-spec-item__label">ERP Integration</span>
                <strong className="cw-spec-item__val cw-val--disconnected">{order.integration_label}</strong>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Milestone 3: Shipment & Tracking */}
      {order && (
        <div className="cw-milestone-card">
          <div className="cw-milestone-head">
            <div className="cw-milestone-indicator">
              {shipment?.status === 'DELIVERED' ? (
                <span className="cw-milestone-dot cw-milestone-dot--done">✓</span>
              ) : shipment ? (
                <span className="cw-milestone-dot cw-milestone-dot--active">3</span>
              ) : (
                <span className="cw-milestone-dot cw-milestone-dot--pending">3</span>
              )}
              <div>
                <h4 className="cw-milestone-title">Milestone 3: Simulated Shipment &amp; Tracking</h4>
                <span className="cw-milestone-sub">Demonstrates the future shipment and tracking lifecycle using synthetic carrier events</span>
              </div>
            </div>
            {shipment && (
              <span className="cw-status-badge cw-status-badge--info">{shipment.status}</span>
            )}
          </div>

          {shipmentError && <div className="cw-alert cw-alert--error">⚠️ {shipmentError}</div>}

          {!shipment && (
            <div className="cw-milestone-body">
              <p>Simulated order recorded. Create a simulated shipment record (no carrier booking is made).</p>
              <button
                type="button"
                className="cw-btn cw-btn--confirm"
                onClick={handleCreateShipment}
                disabled={shipmentLoading}
              >
                {shipmentLoading ? 'Creating Simulated Shipment...' : 'Create Simulated Shipment →'}
              </button>
            </div>
          )}

          {shipment && (
            <div className="cw-shipment-block">
              <div className="cw-milestone-info">
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Demo Tracking Code</span>
                  <strong className="cw-spec-item__val"><code>{shipment.tracking_number}</code></strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Carrier Partner</span>
                  <strong className="cw-spec-item__val">Demo European Logistics Partner</strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">ETA / Delivered</span>
                  <strong className="cw-spec-item__val cw-val--eta">
                    {shipment.status === 'DELIVERED' && shipment.delivered_at
                      ? `Delivered: ${new Date(shipment.delivered_at).toLocaleDateString('en-GB')}`
                      : shipment.eta
                      ? new Date(shipment.eta).toLocaleDateString('en-GB')
                      : 'In Transit'}
                  </strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Connection Status</span>
                  <strong className="cw-spec-item__val cw-val--disconnected">NOT_CONNECTED</strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Tracking Data</span>
                  <strong className="cw-spec-item__val cw-val--disconnected">SYNTHETIC_DEMO</strong>
                </div>
              </div>

              {/* Carrier Simulation Action Controls */}
              <div className="cw-sim-controls">
                {shipment.status === 'CREATED' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--primary cw-btn--sm"
                    onClick={handleDispatchShipment}
                    disabled={shipmentLoading}
                  >
                    {shipmentLoading ? 'Updating...' : 'Simulate Dispatch Milestone →'}
                  </button>
                )}
                {shipment.status === 'DISPATCHED' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--confirm cw-btn--sm"
                    onClick={handleDeliverShipment}
                    disabled={shipmentLoading}
                  >
                    {shipmentLoading ? 'Updating...' : 'Simulate Delivery Milestone →'}
                  </button>
                )}
                {shipment.status === 'DELIVERED' && (
                  <div className="cw-delivered-tag">✓ Demonstration shipment reached the simulated delivery milestone.</div>
                )}
              </div>

              {/* Events timeline */}
              {shipment.events && shipment.events.length > 0 && (
                <div className="cw-events-timeline">
                  <span className="cw-events-title">Simulated Tracking Events (SYNTHETIC_DEMO):</span>
                  <ul className="cw-events-list">
                    {shipment.events.map((e, idx) => (
                      <li key={idx} className="cw-event-item">
                        <span className="cw-event-type">[{e.event_type}]</span>
                        <span className="cw-event-desc">{simulatedShipmentEvent(e.event_type)}</span>
                        {e.location && <span className="cw-event-loc">(simulated location: {e.location})</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Milestone 4: Dealer Service & Workshop */}
      {shipment && (
        <div className="cw-milestone-card">
          <div className="cw-milestone-head">
            <div className="cw-milestone-indicator">
              {serviceJob?.status === 'COMPLETED' ? (
                <span className="cw-milestone-dot cw-milestone-dot--done">✓</span>
              ) : serviceJob ? (
                <span className="cw-milestone-dot cw-milestone-dot--active">4</span>
              ) : (
                <span className="cw-milestone-dot cw-milestone-dot--pending">4</span>
              )}
              <div>
                <h4 className="cw-milestone-title">Milestone 4: Simulated Dealer Service</h4>
                <span className="cw-milestone-sub">Demonstrates the future dealer workshop service lifecycle using synthetic service events</span>
              </div>
            </div>
            {serviceJob && (
              <span className="cw-status-badge cw-status-badge--success">{serviceJob.status}</span>
            )}
          </div>

          {serviceError && <div className="cw-alert cw-alert--error">⚠️ {serviceError}</div>}

          {!serviceJob && (
            <div className="cw-milestone-body">
              <p>Simulated shipment recorded. Create a demo service job (no dealer system is contacted).</p>
              <button
                type="button"
                className="cw-btn cw-btn--primary"
                onClick={handleCreateServiceJob}
                disabled={serviceLoading}
              >
                {serviceLoading ? 'Creating Demo Service Job...' : '[SIMULATED] Create Demo Service Job →'}
              </button>
            </div>
          )}

          {serviceJob && (
            <div className="cw-service-block">
              <div className="cw-milestone-info">
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Demo Work Order</span>
                  <strong className="cw-spec-item__val">
                    <code>{serviceJob.work_order_number || serviceJob.service_job_id}</code>
                  </strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Dealer Branch</span>
                  <strong className="cw-spec-item__val">{serviceJob.dealer_name || dealerName || dealerId}</strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Service Type</span>
                  <strong className="cw-spec-item__val">{serviceJob.service_type}</strong>
                </div>
                <div className="cw-spec-item">
                  <span className="cw-spec-item__label">Data Source</span>
                  <strong className="cw-spec-item__val cw-val--disconnected">DEMO / SIMULATED — dealer DMS/service system NOT_CONNECTED</strong>
                </div>
              </div>

              {/* Service Step Actions */}
              <div className="cw-sim-controls">
                {serviceJob.status === 'OPEN' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--confirm cw-btn--sm"
                    onClick={handleReceivePart}
                    disabled={serviceLoading || shipment?.status !== 'DELIVERED'}
                    title={shipment?.status !== 'DELIVERED' ? 'The simulated shipment must reach the delivery milestone first' : ''}
                  >
                    {serviceLoading ? 'Processing...' : '1. [SIMULATED] Part Receipt Recorded →'}
                  </button>
                )}

                {serviceJob.status === 'PART_RECEIVED' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--primary cw-btn--sm"
                    onClick={handleStartService}
                    disabled={serviceLoading}
                  >
                    {serviceLoading ? 'Processing...' : '2. [SIMULATED] Service Work Started →'}
                  </button>
                )}

                {serviceJob.status === 'IN_PROGRESS' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--primary cw-btn--sm"
                    onClick={handleInstallPart}
                    disabled={serviceLoading}
                  >
                    {serviceLoading ? 'Processing...' : '3. [SIMULATED] Installation Milestone Recorded →'}
                  </button>
                )}

                {serviceJob.status === 'PART_INSTALLED' && (
                  <button
                    type="button"
                    className="cw-btn cw-btn--confirm cw-btn--sm"
                    onClick={handleCompleteService}
                    disabled={serviceLoading}
                  >
                    {serviceLoading ? 'Processing...' : '4. [SIMULATED] Service Completion Recorded →'}
                  </button>
                )}
              </div>

              {/* Events timeline */}
              {serviceJob.events && serviceJob.events.length > 0 && (
                <div className="cw-events-timeline">
                  <span className="cw-events-title">Simulated Service Milestones (SYNTHETIC_DEMO):</span>
                  <ul className="cw-events-list">
                    {serviceJob.events.map((e, idx) => (
                      <li key={idx} className="cw-event-item">
                        <span className="cw-event-type">[{e.event_type}]</span>
                        <span className="cw-event-desc">{simulatedServiceEvent(e.event_type)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Milestone 5: Journey Closed Celebration */}
      {isClosed && (
        <div className="cw-card cw-card--celebration">
          <div className="cw-celebration-head">
            <div className="cw-celebration-badge">✓</div>
            <div>
              <h3 className="cw-celebration-title">Demonstration Fulfilment Journey Completed</h3>
              <p className="cw-celebration-sub">
                This demonstration completed the modeled allocation → order → shipment → dealer service lifecycle using synthetic
                operational data. No live commercial order, carrier shipment, or dealer service event was created.
              </p>
            </div>
          </div>

          <div className="cw-specs-grid" style={{ marginTop: '1rem' }}>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Demo Order ID</span>
              <strong className="cw-spec-item__val"><code>{order?.id}</code></strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Demo Tracking Code</span>
              <strong className="cw-spec-item__val"><code>{shipment?.tracking_number}</code></strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Demo Work Order</span>
              <strong className="cw-spec-item__val"><code>{serviceJob?.work_order_number}</code></strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Demo Status</span>
              <strong className="cw-spec-item__val cw-val--disconnected">DEMO / SIMULATED — FULFILMENT_CLOSED</strong>
            </div>
          </div>

          <div className="cw-actions" style={{ marginTop: '1.2rem' }}>
            <button type="button" className="cw-btn cw-btn--primary" onClick={onFinishJourney}>
              Return to Parts Store
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
