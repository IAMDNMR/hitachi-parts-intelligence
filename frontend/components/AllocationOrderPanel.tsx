import { simulatedServiceEvent, simulatedShipmentEvent } from './simulatedEvents'
import { useState } from 'react'
import type { AllocationResult, OrderResult, ApiErrorBody } from '../types/api'
import { formatOrderPrice } from './orderDisplay'

interface ShipmentData {
  shipment_id: string
  order_id: string
  status: string
  carrier: string
  tracking_number: string
  origin?: string
  destination?: string
  eta?: string
  shipped_at?: string
  delivered_at?: string
  synthetic: boolean
  integration_label: string
  events: {
    id: string
    event_type: string
    description: string
    location?: string
    timestamp: string
  }[]
}

interface ServiceJobData {
  service_job_id: string
  order_id: string
  shipment_id?: string
  dealer_id: string
  dealer_name?: string
  dealer_city?: string
  dealer_country?: string
  status: string
  service_type: string
  work_order_number?: string
  notes?: string
  received_at?: string
  started_at?: string
  installed_at?: string
  completed_at?: string
  synthetic: boolean
  events: {
    id: string
    event_type: string
    description: string
    technician_role?: string
    timestamp: string
  }[]
}

interface AllocationOrderPanelProps {
  requestId: string
  partNumber: string
  quantity: number
  sourceId: string
}

/**
 * Phase 6 Allocation + Order & Phase 7 Shipment + Tracking & Phase 8 Dealer Service & Close.
 * Matches the existing HCME dark-card design system — no new colors/theme.
 */
export default function AllocationOrderPanel({
  requestId,
  partNumber,
  quantity,
  sourceId,
}: AllocationOrderPanelProps) {
  const [allocLoading, setAllocLoading] = useState(false)
  const [allocation, setAllocation] = useState<AllocationResult | null>(null)
  const [allocError, setAllocError] = useState<string | null>(null)

  const [orderLoading, setOrderLoading] = useState(false)
  const [order, setOrder] = useState<OrderResult | null>(null)
  const [orderError, setOrderError] = useState<string | null>(null)

  const [shipmentLoading, setShipmentLoading] = useState(false)
  const [shipment, setShipment] = useState<ShipmentData | null>(null)
  const [shipmentError, setShipmentError] = useState<string | null>(null)

  const [serviceLoading, setServiceLoading] = useState(false)
  const [serviceJob, setServiceJob] = useState<ServiceJobData | null>(null)
  const [serviceError, setServiceError] = useState<string | null>(null)

  const authHeaders = {
    'Content-Type': 'application/json',
    'x-test-user-id': 'site-visitor-demo',
    'x-test-role': 'CUSTOMER',
  }

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
        const errBody = data as ApiErrorBody
        throw new Error(errBody.error?.message || 'Allocation failed.')
      }
      setAllocation(data as AllocationResult)
    } catch (err) {
      setAllocError(err instanceof Error ? err.message : String(err))
    } finally {
      setAllocLoading(false)
    }
  }

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
        const errBody = data as ApiErrorBody
        throw new Error(errBody.error?.message || 'Order creation failed.')
      }
      setOrder(data as OrderResult)
    } catch (err) {
      setOrderError(err instanceof Error ? err.message : String(err))
    } finally {
      setOrderLoading(false)
    }
  }

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
      if (!res.ok) {
        throw new Error(data.detail || data.error?.message || 'Shipment creation failed.')
      }
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  const handleDispatchShipment = async () => {
    if (!shipment) return
    setShipmentLoading(true)
    try {
      const res = await fetch(`/api/v1/shipments/${shipment.shipment_id}/dispatch`, {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Dispatch failed')
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  const handleDeliverShipment = async () => {
    if (!shipment) return
    setShipmentLoading(true)
    try {
      const res = await fetch(`/api/v1/shipments/${shipment.shipment_id}/deliver`, {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Delivery confirmation failed')
      setShipment(data as ShipmentData)
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : String(err))
    } finally {
      setShipmentLoading(false)
    }
  }

  // Phase 8 Service Handlers
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

  return (
    <div className="alloc-panel">
      <div className="alloc-panel__head">
        <h4>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Fulfilment Journey: Allocation → Order → Shipment → Service → Close
        </h4>
      </div>

      <div className="alloc-summary">
        <div>
          <span>Part</span>
          <strong>{partNumber}</strong>
        </div>
        <div>
          <span>Quantity</span>
          <strong>{quantity}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{sourceId}</strong>
        </div>
        <div>
          <span>Fulfilment Request</span>
          <strong className="alloc-summary__truncate">{requestId}</strong>
        </div>
      </div>

      {allocError && <div className="avail-alert avail-alert--error">Allocation error: {allocError}</div>}

      {!allocation && (
        <button type="button" disabled={allocLoading} onClick={handleAllocate} className="avail-btn avail-btn--confirm">
          {allocLoading ? 'Allocating…' : 'Allocate Inventory'}
        </button>
      )}

      {allocation && (
        <div className="fulfil-confirmed">
          <strong>Allocation {allocation.status}.</strong> Allocation ID:{' '}
          <span className="fulfil-confirmed__code">{allocation.allocation_id}</span>
        </div>
      )}

      {allocation && allocation.status === 'CONFIRMED' && (
        <>
          {orderError && <div className="avail-alert avail-alert--error">Order error: {orderError}</div>}

          {!order && (
            <div className="alloc-order-step">
              <p>
                Review before placing your order. This is a TEST/DEVELOPMENT order workflow — no real
                HCME order system is connected yet.
              </p>
              <button type="button" disabled={orderLoading} onClick={handlePlaceOrder} className="avail-btn avail-btn--primary">
                {orderLoading ? 'Placing order…' : 'Place Order'}
              </button>
            </div>
          )}

          {order && (
            <div className="alloc-order-result">
              <div className="alloc-order-result__row">
                <span className="fulfil-tag fulfil-tag--confirmed">{order.status}</span>
                <span className="alloc-order-result__id">{order.id}</span>
              </div>
              <div className="alloc-order-result__price">
                Price: <span>{formatOrderPrice(order)}</span>
              </div>
              <div className="alloc-order-result__note">{order.integration_label}</div>

              {/* Phase 7 Shipment & Tracking Section */}
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #334155' }}>
                <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Simulated Shipment &amp; Tracking (SYNTHETIC_DEMO)
                </h5>

                {shipmentError && <div className="avail-alert avail-alert--error">Shipment error: {shipmentError}</div>}

                {!shipment && (
                  <button
                    type="button"
                    disabled={shipmentLoading}
                    onClick={handleCreateShipment}
                    className="avail-btn avail-btn--confirm"
                    style={{ marginTop: '8px' }}
                  >
                    {shipmentLoading ? 'Creating Shipment…' : 'Create & Dispatch Shipment →'}
                  </button>
                )}

                {shipment && (
                  <div style={{ background: '#0f172a', padding: '12px', borderRadius: '6px', marginTop: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="fulfil-tag fulfil-tag--confirmed">{shipment.status}</span>
                      <strong style={{ fontSize: '13px', color: '#f8fafc' }}>
                        Tracking: {shipment.tracking_number}
                      </strong>
                    </div>
                    <p style={{ margin: '6px 0', fontSize: '12px', color: '#cbd5e1' }}>
                      Carrier: {shipment.carrier} · {shipment.status === 'DELIVERED' && shipment.delivered_at ? `Delivered: ${new Date(shipment.delivered_at).toLocaleDateString('en-GB')}` : `ETA: ${shipment.eta ? new Date(shipment.eta).toLocaleDateString('en-GB') : 'Pending'}`}
                    </p>
                    <div style={{ fontSize: '11px', color: '#f59e0b', margin: '4px 0' }}>
                      {shipment.integration_label}
                    </div>

                    {/* Timeline of events */}
                    <div style={{ marginTop: '10px' }}>
                      <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase' }}>
                        Simulated Tracking Events:
                      </span>
                      <ul style={{ listStyle: 'none', padding: 0, margin: '4px 0', fontSize: '12px' }}>
                        {shipment.events.map((e, idx) => (
                          <li key={idx} style={{ padding: '3px 0', color: '#94a3b8' }}>
                            <strong style={{ color: '#e2e8f0' }}>[{e.event_type}]</strong> {simulatedShipmentEvent(e.event_type)}{' '}
                            {e.location && <span style={{ color: '#64748b' }}>({e.location})</span>}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Action buttons for simulation */}
                    <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                      {shipment.status === 'CREATED' && (
                        <button
                          type="button"
                          disabled={shipmentLoading}
                          onClick={handleDispatchShipment}
                          className="avail-btn avail-btn--primary"
                          style={{ fontSize: '12px', padding: '6px 10px' }}
                        >
                          Simulate Carrier Dispatch
                        </button>
                      )}
                      {shipment.status === 'DISPATCHED' && (
                        <button
                          type="button"
                          disabled={shipmentLoading}
                          onClick={handleDeliverShipment}
                          className="avail-btn avail-btn--confirm"
                          style={{ fontSize: '12px', padding: '6px 10px' }}
                        >
                          Confirm Delivery
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Phase 8 Dealer Service & Close Section */}
              {shipment && (
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #334155' }}>
                  <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#38bdf8', textTransform: 'uppercase' }}>
                    Dealer Service &amp; Close
                  </h5>

                  {serviceError && <div className="avail-alert avail-alert--error">Service error: {serviceError}</div>}

                  {!serviceJob && (
                    <button
                      type="button"
                      disabled={serviceLoading}
                      onClick={handleCreateServiceJob}
                      className="avail-btn avail-btn--primary"
                      style={{ marginTop: '8px' }}
                    >
                      {serviceLoading ? 'Creating Service Job…' : 'Register Dealer Service Job →'}
                    </button>
                  )}

                  {serviceJob && (
                    <div style={{ background: '#091e3a', border: '1px solid #1e3a8a', padding: '12px', borderRadius: '6px', marginTop: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className="fulfil-tag fulfil-tag--confirmed">{serviceJob.status}</span>
                        <strong style={{ fontSize: '13px', color: '#67e8f9' }}>
                          Work Order: {serviceJob.work_order_number || serviceJob.service_job_id}
                        </strong>
                      </div>
                      <p style={{ margin: '6px 0', fontSize: '12px', color: '#93c5fd' }}>
                        Dealer: {serviceJob.dealer_name || serviceJob.dealer_id} · Type: {serviceJob.service_type}
                      </p>

                      {/* Service Events */}
                      <div style={{ marginTop: '10px' }}>
                        <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>
                          Service Milestones:
                        </span>
                        <ul style={{ listStyle: 'none', padding: 0, margin: '4px 0', fontSize: '12px' }}>
                          {serviceJob.events.map((e, idx) => (
                            <li key={idx} style={{ padding: '3px 0', color: '#cbd5e1' }}>
                              <strong style={{ color: '#38bdf8' }}>[{e.event_type}]</strong> {simulatedServiceEvent(e.event_type)}
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Service Action Buttons */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
                        {serviceJob.status === 'OPEN' && (
                          <button
                            type="button"
                            disabled={serviceLoading || shipment.status !== 'DELIVERED'}
                            onClick={handleReceivePart}
                            className="avail-btn avail-btn--confirm"
                            style={{ fontSize: '12px', padding: '6px 10px' }}
                            title={shipment.status !== 'DELIVERED' ? 'Requires Shipment DELIVERED first' : ''}
                          >
                            1. Confirm Part Receipt
                          </button>
                        )}
                        {serviceJob.status === 'PART_RECEIVED' && (
                          <button
                            type="button"
                            disabled={serviceLoading}
                            onClick={handleStartService}
                            className="avail-btn avail-btn--primary"
                            style={{ fontSize: '12px', padding: '6px 10px' }}
                          >
                            2. Start Technician Service
                          </button>
                        )}
                        {serviceJob.status === 'IN_PROGRESS' && (
                          <button
                            type="button"
                            disabled={serviceLoading}
                            onClick={handleInstallPart}
                            className="avail-btn avail-btn--primary"
                            style={{ fontSize: '12px', padding: '6px 10px' }}
                          >
                            3. [SIMULATED] Installation Milestone Recorded
                          </button>
                        )}
                        {serviceJob.status === 'PART_INSTALLED' && (
                          <button
                            type="button"
                            disabled={serviceLoading}
                            onClick={handleCompleteService}
                            className="avail-btn avail-btn--confirm"
                            style={{ fontSize: '12px', padding: '6px 10px' }}
                          >
                            4. [SIMULATED] Service Completion Recorded
                          </button>
                        )}
                        {serviceJob.status === 'COMPLETED' && (
                          <div style={{ color: '#4ade80', fontSize: '12px', fontWeight: 'bold', padding: '4px 0' }}>
                            ✓ Demonstration Fulfilment Journey Completed (DEMO / SIMULATED - no live order, shipment or service event)
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

