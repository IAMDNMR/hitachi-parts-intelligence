export interface PlacedOrder {
  order_id: string
  status: string
  customer_name: string
  customer_email: string
  customer_phone?: string | null
  dealer_name?: string | null
  ship_to_address?: string | null
  ship_to_city?: string | null
  ship_to_country?: string | null
  parts: { part_number: string; part_name?: string | null; quantity: number }[]
  fulfilment_mode?: string | null
  fulfilment_service_level?: string | null
  fulfilment_transit_days?: number | null
  fulfilment_eta?: string | null
  fulfilment_cost?: number | null
  fulfilment_currency?: string | null
  placed_at: string
}

const STATUS_LABEL: Record<string, string> = { CREATED: 'Placed' }

export default function Stage7OrderConfirmation({ order, onFinish }: { order: PlacedOrder; onFinish: () => void }) {
  const placed = new Date(order.placed_at)
  const part = order.parts[0]
  const shipTo = [
    order.dealer_name,
    order.ship_to_address,
    [order.ship_to_city, order.ship_to_country].filter(Boolean).join(', '),
  ].filter(Boolean)
  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--synthetic">SYNTHETIC DEMO · ORDER PLACED</div>
        <h3 className="cw-stage__title">7. Order Confirmation</h3>
        <p className="cw-stage__desc">
          Your order has been placed and saved. HCME operations will now allocate, ship and deliver it — you do not need to do anything else.
        </p>
      </div>

      <div className="cw-card cw-card--review-section" data-testid="order-confirmation">
        <div className="cw-review-rows">
          <div className="cw-review-row">
            <span>Order ID</span>
            <strong className="cw-val--price" data-testid="order-id">{order.order_id}</strong>
          </div>
          <div className="cw-review-row"><span>Status</span><strong>{STATUS_LABEL[order.status] ?? order.status}</strong></div>
          <div className="cw-review-row">
            <span>Placed</span>
            <span>{placed.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })}</span>
          </div>
          <div className="cw-review-row"><span>Customer</span><span>{order.customer_name}</span></div>
          <div className="cw-review-row"><span>Email</span><span>{order.customer_email}</span></div>
          {order.customer_phone && <div className="cw-review-row"><span>Phone</span><span>{order.customer_phone}</span></div>}
          <div className="cw-review-row">
            <span>Part</span>
            <span>{part?.part_name ?? part?.part_number} ({part?.part_number}) × {part?.quantity}</span>
          </div>
          <div className="cw-review-row"><span>Deliver to</span><span>{shipTo.join(' · ')}</span></div>
          {order.fulfilment_mode && (
            <div className="cw-review-row">
              <span>Fulfilment</span>
              <span>
                {order.fulfilment_mode} {order.fulfilment_service_level}
                {order.fulfilment_transit_days != null
                  ? ` · ${order.fulfilment_transit_days} business day${order.fulfilment_transit_days === 1 ? '' : 's'}`
                  : ''}
                {order.fulfilment_cost != null
                  ? ` · €${Number(order.fulfilment_cost).toFixed(2)} ${order.fulfilment_currency ?? 'EUR'} freight`
                  : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="cw-actions">
        <span />
        <button type="button" className="cw-btn cw-btn--confirm" onClick={onFinish}>Done</button>
      </div>
    </div>
  )
}
