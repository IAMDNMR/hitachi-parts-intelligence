import type { CartItem } from '../../types/api'

interface Stage1CartProps {
  item: CartItem
  onUpdateQty: (qty: number) => void
  onNext: () => void
  onClose: () => void
}

export default function Stage1Cart({ item, onUpdateQty, onNext, onClose }: Stage1CartProps) {
  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        {item.partNumber?.toUpperCase().startsWith('DEMO-') ? (
          <div className="cw-stage__badge cw-stage__badge--synthetic">SYNTHETIC DEMO · DEMO PART REFERENCE</div>
        ) : (
          <div className="cw-stage__badge cw-stage__badge--real">REAL · GENUINE CATALOGUE ITEM</div>
        )}
        <h3 className="cw-stage__title">2. Cart</h3>
        <p className="cw-stage__desc">
          Check the part and the quantity before choosing where to deliver it.
        </p>
      </div>

      <div className="cw-card cw-card--item">
        <div className="cw-card__item-media">
          {item.image ? (
            <img src={item.image} alt={item.name} className="cw-card__item-img" />
          ) : (
            <div className="cw-card__item-placeholder">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                <line x1="12" y1="22.08" x2="12" y2="12" />
              </svg>
            </div>
          )}
        </div>

        <div className="cw-card__item-content">
          <div className="cw-card__item-header">
            <h4>{item.name}</h4>
            {item.partNumber?.toUpperCase().startsWith('DEMO-') ? (
              <span className="cw-tag cw-tag--amber">DEMO PART REFERENCE — NOT AN OFFICIAL HCME PART NUMBER</span>
            ) : (
              <span className="cw-tag cw-tag--green">GENUINE HITACHI OEM</span>
            )}
          </div>

          <div className="cw-specs-grid">
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Part Number</span>
              <strong className="cw-spec-item__val">{item.partNumber || item.id}</strong>
            </div>
            {item.machine && (
              <div className="cw-spec-item">
                <span className="cw-spec-item__label">Machine Model Context</span>
                <strong className="cw-spec-item__val">{item.machine}</strong>
              </div>
            )}
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Provenance</span>
              {item.partNumber?.toUpperCase().startsWith('DEMO-') ? (
                <strong className="cw-spec-item__val">Demo reference</strong>
              ) : (
                <strong className="cw-spec-item__val cw-val--real">Source-Verified Catalog</strong>
              )}
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Origin Depot</span>
              <strong className="cw-spec-item__val">European Parts Centre (Oosterhout, NL)</strong>
            </div>
          </div>

          <div className="cw-qty-selector">
            <span className="cw-qty-selector__label">Order Quantity:</span>
            <div className="cw-qty-controls">
              <button
                type="button"
                className="cw-qty-btn"
                onClick={() => onUpdateQty(Math.max(1, item.qty - 1))}
                disabled={item.qty <= 1}
                aria-label="Decrease quantity"
              >
                −
              </button>
              <span className="cw-qty-value">{item.qty}</span>
              <button
                type="button"
                className="cw-qty-btn"
                onClick={() => onUpdateQty(item.qty + 1)}
                aria-label="Increase quantity"
              >
                +
              </button>
            </div>
            <span className="cw-qty-unit">unit{item.qty > 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      <div className="cw-actions">
        <button type="button" className="cw-btn cw-btn--secondary" onClick={onClose}>
          ← Back
        </button>
        <button type="button" className="cw-btn cw-btn--primary" onClick={onNext}>
          Next: Delivery Dealer →
        </button>
      </div>
    </div>
  )
}
