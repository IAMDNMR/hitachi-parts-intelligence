import type {
  CartItem,
  DealerOption,
  TransportComparisonResponse,
  TransportOptionDTO,
} from '../../types/api'
import type { UnifiedTransportOption } from './Stage5Transportation'

interface Stage6OrderReviewProps {
  item: CartItem
  requesterName: string
  requesterEmail: string
  requesterCompany?: string
  dealer: DealerOption | null
  transportComparison: TransportComparisonResponse | null
  selectedOption: UnifiedTransportOption | TransportOptionDTO | null
  onBack: () => void
  onConfirmOrder: () => void
  submitting: boolean
  error: string | null
}

export default function Stage6OrderReview({
  item,
  requesterName,
  requesterEmail,
  requesterCompany,
  dealer,
  transportComparison,
  selectedOption,
  onBack,
  onConfirmOrder,
  submitting,
  error,
}: Stage6OrderReviewProps) {
  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--info">ORDER PRE-CONFIRMATION</div>
        <h3 className="cw-stage__title">6. Final Review &amp; Order Authorization</h3>
        <p className="cw-stage__desc">
          Review the complete fulfilment request specification before confirming inventory allocation and creating the
          order.
        </p>
      </div>

      <div className="cw-provenance-banner cw-provenance-banner--synthetic">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <div>
          <strong>DEVELOPMENT &amp; TEST WORKFLOW:</strong> Placing this order writes real entities to the Neo4j AuraDB graph.
          Commercial SAP ERP ordering is <span className="cw-highlight-disconnected">NOT CONNECTED</span>.
        </div>
      </div>

      {error && <div className="cw-alert cw-alert--error">⚠️ {error}</div>}

      <div className="cw-review-grid">
        {/* Column 1: Order Items & Requester */}
        <div className="cw-review-col">
          <div className="cw-card cw-card--review-section">
            <h4 className="cw-review-section__title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              </svg>
              1. Part Specification
            </h4>
            <div className="cw-review-rows">
              <div className="cw-review-row">
                <span>Part Name</span>
                <strong>{item.name}</strong>
              </div>
              <div className="cw-review-row">
                <span>Part Number</span>
                <code>{item.partNumber || item.id}</code>
              </div>
              {item.machine && (
                <div className="cw-review-row">
                  <span>Machine Compatibility</span>
                  <span>{item.machine}</span>
                </div>
              )}
              <div className="cw-review-row">
                <span>Quantity</span>
                <strong>{item.qty} unit{item.qty > 1 ? 's' : ''}</strong>
              </div>
              <div className="cw-review-row">
                <span>Origin Depot</span>
                <span>Hitachi European Parts Centre (Oosterhout, NL)</span>
              </div>
            </div>
          </div>

          <div className="cw-card cw-card--review-section">
            <h4 className="cw-review-section__title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              2. Requester Details
            </h4>
            <div className="cw-review-rows">
              <div className="cw-review-row">
                <span>Contact Name</span>
                <strong>{requesterName}</strong>
              </div>
              <div className="cw-review-row">
                <span>Email Address</span>
                <span>{requesterEmail}</span>
              </div>
              {requesterCompany && (
                <div className="cw-review-row">
                  <span>Customer / Fleet</span>
                  <span>{requesterCompany}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Column 2: Destination & Transportation */}
        <div className="cw-review-col">
          <div className="cw-card cw-card--review-section">
            <h4 className="cw-review-section__title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              3. Receiving Dealer Branch
            </h4>
            <div className="cw-review-rows">
              <div className="cw-review-row">
                <span>Branch Name</span>
                <strong>{dealer?.dealer_name || 'Dealer Branch'}</strong>
              </div>
              <div className="cw-review-row">
                <span>Dealer ID</span>
                <code>{dealer?.dealer_id}</code>
              </div>
              <div className="cw-review-row">
                <span>Location</span>
                <span>
                  {dealer?.city ? `${dealer.city}, ` : ''}
                  {dealer?.country}
                </span>
              </div>
              <div className="cw-review-row">
                <span>Straight-Line Distance</span>
                <span className="cw-val--derived">
                  {transportComparison?.straight_line_distance_km ?? dealer?.distance_km} km
                </span>
              </div>
              <div className="cw-review-row">
                <span>Estimated Road Distance</span>
                <span className="cw-val--derived">
                  {transportComparison?.estimated_road_distance_km} km (1.25× factor)
                </span>
              </div>
            </div>
          </div>

          <div className="cw-card cw-card--review-section">
            <h4 className="cw-review-section__title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="1" y="3" width="15" height="13" />
                <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
                <circle cx="5.5" cy="18.5" r="2.5" />
                <circle cx="18.5" cy="18.5" r="2.5" />
              </svg>
              4. Transportation &amp; Delivery
            </h4>
            <div className="cw-review-rows">
              <div className="cw-review-row">
                <span>Selected Mode</span>
                <strong>{selectedOption?.display_name || 'Road Freight'}</strong>
              </div>
              <div className="cw-review-row">
                <span>Service Level</span>
                <span>{selectedOption?.service_level}</span>
              </div>
              <div className="cw-review-row">
                <span>Transit Duration</span>
                <strong>
                  {selectedOption?.transit_days} {selectedOption?.transit_days === 1 ? 'business day' : 'business days'}
                </strong>
              </div>
              <div className="cw-review-row">
                <span>Estimated Delivery (ETA)</span>
                <strong className="cw-val--eta">
                  {selectedOption?.estimated_delivery_date
                    ? new Date(selectedOption.estimated_delivery_date).toLocaleDateString('en-GB', {
                        weekday: 'short',
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })
                    : '—'}
                </strong>
              </div>
              <div className="cw-review-row">
                <span>Freight Price</span>
                <strong className="cw-val--price">€{selectedOption?.total_cost.toFixed(2)} EUR</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="cw-actions">
        <button type="button" className="cw-btn cw-btn--secondary" onClick={onBack} disabled={submitting}>
          ← Back to Transportation
        </button>
        <button
          type="button"
          className="cw-btn cw-btn--confirm"
          onClick={onConfirmOrder}
          disabled={submitting}
        >
          {submitting ? 'Placing Order & Allocating...' : 'Confirm Order & Proceed to Fulfilment →'}
        </button>
      </div>
    </div>
  )
}
