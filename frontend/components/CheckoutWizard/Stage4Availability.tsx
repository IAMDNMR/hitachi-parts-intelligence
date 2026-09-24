import type { AvailabilitySource } from '../../types/api'

interface Stage4AvailabilityProps {
  loading: boolean
  error: string | null
  sources: AvailabilitySource[] | null
  requiredQty: number
  partNumber: string
  onRetry: () => void
  onBack: () => void
  onNext: () => void
}

export default function Stage4Availability({
  loading,
  error,
  sources,
  requiredQty,
  partNumber,
  onRetry,
  onBack,
  onNext,
}: Stage4AvailabilityProps) {
  const badgeTone = (status: string | undefined, isStale: boolean | undefined) => {
    if (isStale) return 'cw-status-badge--warning'
    switch (status) {
      case 'AVAILABLE':
        return 'cw-status-badge--success'
      case 'UNAVAILABLE':
        return 'cw-status-badge--danger'
      default:
        return 'cw-status-badge--neutral'
    }
  }


  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--synthetic">SYNTHETIC DEMO · AVAILABILITY SNAPSHOT</div>
        <h3 className="cw-stage__title">4. Availability</h3>
        <p className="cw-stage__desc">
          Availability snapshot for part <strong>{partNumber}</strong> (quantity: <strong>{requiredQty}</strong>) evaluated against European depot and regional network sources.
        </p>
      </div>

      <div className="cw-provenance-banner cw-provenance-banner--synthetic">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <div>
          <strong>DATA PROVENANCE NOTICE:</strong> Inventory levels shown are{' '}
          <span className="cw-highlight-synthetic">SYNTHETIC DEMO DATA</span>. Live connection to{' '}
          <span className="cw-highlight-disconnected">SAP ERP / LIVE INVENTORY NOT CONNECTED</span>.
        </div>
      </div>

      {loading && (
        <div className="cw-loading-card">
          <div className="cw-spinner" />
          <p>Evaluating inventory sources and checking availability snapshots...</p>
        </div>
      )}

      {error && (
        <div className="cw-alert cw-alert--error">
          <p>⚠️ {error}</p>
          <button type="button" className="cw-btn cw-btn--secondary" onClick={onRetry}>
            Retry Check
          </button>
        </div>
      )}

      {!loading && sources && sources.length > 0 && (
        <div className="cw-sources-list">
          <div className="cw-sources-list__head">
            <h5>Availability Snapshot by Fulfilment Location</h5>
            <span className="cw-sources-count">{sources.length} locations checked</span>
          </div>

          <div className="cw-sources-grid">
            {sources.map((src) => (
              <div key={src.source_id} className="cw-card cw-card--source">
                <div className="cw-card__source-head">
                  <div>
                    <h5 className="cw-card__source-title">{src.source_name || src.source_id}</h5>
                    <span className="cw-card__source-type">
                      {src.source_type} · ID: <code>{src.source_id}</code>
                    </span>
                  </div>
                  <span className={`cw-status-badge ${badgeTone(src.status, src.is_stale)}`}>
                    {src.is_stale ? 'STALE DATA' : src.status}
                  </span>
                </div>

                <div className="cw-source-details">
                  <div className="cw-source-qty">
                    <span className="cw-source-qty__num">{src.available_qty}</span>
                    <span className="cw-source-qty__lbl">units available</span>
                  </div>
                  <div className="cw-source-time">
                    As of: {new Date(src.inventory_timestamp).toLocaleTimeString('en-GB')}
                  </div>
                </div>

                <div className="cw-source-footer">
                  <span className="cw-tag cw-tag--synthetic">SYNTHETIC_DEMO</span>
                  {src.available_qty >= requiredQty ? (
                    <span className="cw-match-tag cw-match-tag--full">Sufficient for request</span>
                  ) : src.available_qty > 0 ? (
                    <span className="cw-match-tag cw-match-tag--partial">Partial fulfillment</span>
                  ) : (
                    <span className="cw-match-tag cw-match-tag--none">Out of stock</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="cw-actions">
        <button type="button" className="cw-btn cw-btn--secondary" onClick={onBack}>
          ← Back to Dealer
        </button>
        <button
          type="button"
          className="cw-btn cw-btn--primary"
          onClick={onNext}
          disabled={loading || !sources || sources.length === 0}
        >
          Next: Transportation Options →
        </button>
      </div>
    </div>
  )
}
