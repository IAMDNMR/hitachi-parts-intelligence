import type { FulfilmentOption, TransportComparisonResponse } from '../../types/api'

export interface UnifiedTransportOption {
  id: string
  mode: string
  service_level: string
  display_name: string
  carrier_label: string
  transit_days: number
  estimated_delivery_date: string
  dispatch_cutoff_time: string
  currency: string
  total_cost: number
  highlight_tag?: string | null
  straight_line_distance_km?: number
  estimated_road_distance_km?: number
  distance_band_name?: string
}

interface Stage5TransportationProps {
  loading: boolean
  error: string | null
  transportComparison: TransportComparisonResponse | null
  fulfilmentOptions: FulfilmentOption[] | null
  selectedOptionId: string | null
  onSelectOption: (option: UnifiedTransportOption) => void
  onBack: () => void
  onNext: () => void
}

export default function Stage5Transportation({
  loading,
  error,
  transportComparison,
  fulfilmentOptions,
  selectedOptionId,
  onSelectOption,
  onBack,
  onNext,
}: Stage5TransportationProps) {
  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'AIR':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13" />
            <path d="M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        )
      case 'RAIL':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="4" y="3" width="16" height="16" rx="2" />
            <path d="M4 11h16" />
            <path d="M12 3v8" />
            <path d="m8 19-2 3" />
            <path d="m16 19 2 3" />
            <circle cx="8" cy="15" r="1" />
            <circle cx="16" cy="15" r="1" />
          </svg>
        )
      case 'ROAD':
      default:
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="1" y="3" width="15" height="13" />
            <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
            <circle cx="5.5" cy="18.5" r="2.5" />
            <circle cx="18.5" cy="18.5" r="2.5" />
          </svg>
        )
    }
  }

  const getHighlightBadgeClass = (tag: string | null | undefined) => {
    switch (tag) {
      case 'LOWEST COST':
        return 'cw-highlight-badge--lowest-cost'
      case 'FASTEST':
        return 'cw-highlight-badge--fastest'
      default:
        return ''
    }
  }

  // Normalize options from fulfilmentOptions (Neo4j fopt-...) or transportComparison (TR-...)
  const displayOptions: UnifiedTransportOption[] = []

  if (fulfilmentOptions && fulfilmentOptions.length > 0) {
    for (const fopt of fulfilmentOptions) {
      const details = (fopt.details || {}) as Record<string, unknown>
      const mode = fopt.transport_mode || 'ROAD'
      const service = fopt.service_level || 'STANDARD'
      let name = `${mode} ${service}`
      if (mode === 'ROAD' && service === 'STANDARD') name = 'Road Freight Standard'
      else if (mode === 'ROAD' && service === 'EXPRESS') name = 'Road Courier Express'
      else if (mode === 'RAIL') name = 'Rail Intermodal Freight'
      else if (mode === 'AIR') name = 'Air Freight Express'

      displayOptions.push({
        id: fopt.id,
        mode: mode,
        service_level: service,
        display_name: name,
        carrier_label: fopt.carrier_code || 'European Freight Partner · Demo',
        transit_days: fopt.transit_days ?? 3,
        estimated_delivery_date: fopt.eta ?? new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10),
        dispatch_cutoff_time: (details.cutoff_time as string) || '15:00 CET',
        currency: fopt.currency || 'EUR',
        total_cost: fopt.transport_cost ?? 60.0,
        highlight_tag: (details.highlight_tag as string) || null,
        straight_line_distance_km: (details.straight_line_distance_km as number) || transportComparison?.straight_line_distance_km,
        estimated_road_distance_km: (details.estimated_road_distance_km as number) || transportComparison?.estimated_road_distance_km,
        distance_band_name: (details.distance_band_name as string) || transportComparison?.distance_band_name,
      })
    }
  } else if (transportComparison?.options) {
    for (const topt of transportComparison.options) {
      displayOptions.push({
        id: topt.transport_option_id,
        mode: topt.mode,
        service_level: topt.service_level,
        display_name: topt.display_name,
        carrier_label: topt.carrier_label,
        transit_days: topt.transit_days,
        estimated_delivery_date: topt.estimated_delivery_date,
        dispatch_cutoff_time: topt.dispatch_cutoff_time,
        currency: topt.currency,
        total_cost: topt.total_cost,
        highlight_tag: topt.highlight_tag,
        straight_line_distance_km: transportComparison.straight_line_distance_km,
        estimated_road_distance_km: transportComparison.estimated_road_distance_km,
        distance_band_name: transportComparison.distance_band_name,
      })
    }
  }

  const distanceKm =
    transportComparison?.straight_line_distance_km || displayOptions[0]?.straight_line_distance_km
  const roadKm =
    transportComparison?.estimated_road_distance_km || displayOptions[0]?.estimated_road_distance_km
  const bandName =
    transportComparison?.distance_band_name || displayOptions[0]?.distance_band_name

  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--synthetic">SYNTHETIC DEMO · MULTI-MODAL LOGISTICS</div>
        <h3 className="cw-stage__title">5. European Transportation Selection</h3>
        <p className="cw-stage__desc">
          Compare multi-modal freight routes from the European Parts Centre in Oosterhout to the receiving dealer branch.
          Options are calculated using deterministic European distance-band rates.
        </p>
      </div>

      <div className="cw-provenance-banner cw-provenance-banner--synthetic">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <div>
          <strong>PROVENANCE CONTRACT:</strong> Distance is{' '}
          <span className="cw-highlight-derived">DERIVED · STRAIGHT-LINE DISTANCE</span>. Rates, transit times, and ETAs are{' '}
          <span className="cw-highlight-synthetic">SYNTHETIC_DEMO</span>. Live carrier telematics and real TMS are{' '}
          <span className="cw-highlight-disconnected">NOT CONNECTED</span>.
        </div>
      </div>

      {loading && (
        <div className="cw-loading-card">
          <div className="cw-spinner" />
          <p>Calculating multi-modal route options, distance bands, and delivery dates...</p>
        </div>
      )}

      {error && <div className="cw-alert cw-alert--error">⚠️ {error}</div>}

      {!loading && displayOptions.length > 0 && (
        <>
          <div className="cw-route-summary">
            <div className="cw-route-leg">
              <span className="cw-route-leg__label">Origin Depot</span>
              <strong className="cw-route-leg__title">
                {transportComparison?.origin.name || 'Hitachi European Parts Centre'} (
                {transportComparison?.origin.city || 'Oosterhout'}, {transportComparison?.origin.country || 'NL'})
              </strong>
            </div>

            <div className="cw-route-vector">
              <span className="cw-route-vector__line" />
              <div className="cw-route-vector__metrics">
                {distanceKm != null && (
                  <span className="cw-vector-dist cw-val--derived">
                    {distanceKm} km (straight-line)
                  </span>
                )}
                {roadKm != null && (
                  <span className="cw-vector-road cw-val--derived">
                    ~{roadKm} km (road 1.25×)
                  </span>
                )}
                {bandName && <span className="cw-vector-band">{bandName}</span>}
              </div>
            </div>

            <div className="cw-route-leg">
              <span className="cw-route-leg__label">Destination Dealer</span>
              <strong className="cw-route-leg__title">
                {transportComparison?.destination.name || 'Authorised Dealer Branch'} (
                {transportComparison?.destination.city ? `${transportComparison.destination.city}, ` : ''}
                {transportComparison?.destination.country || 'Europe'})
              </strong>
            </div>
          </div>

          <div className="cw-transport-grid">
            {displayOptions.map((opt) => {
              const isSelected = selectedOptionId === opt.id
              return (
                <div
                  key={opt.id}
                  onClick={() => onSelectOption(opt)}
                  className={`cw-card cw-card--transport${isSelected ? ' is-selected' : ''}`}
                >
                  <div className="cw-transport-head">
                    <div className="cw-transport-mode">
                      <span className="cw-transport-mode__icon">{getModeIcon(opt.mode)}</span>
                      <div>
                        <h4 className="cw-transport-mode__name">{opt.display_name}</h4>
                        <span className="cw-transport-mode__service">
                          {opt.service_level} · {opt.carrier_label}
                        </span>
                      </div>
                    </div>

                    {opt.highlight_tag && (
                      <span className={`cw-highlight-badge ${getHighlightBadgeClass(opt.highlight_tag)}`}>
                        {opt.highlight_tag}
                      </span>
                    )}
                  </div>

                  <div className="cw-transport-metrics">
                    <div className="cw-transport-metric">
                      <span className="cw-metric-label">Transit Time</span>
                      <strong className="cw-metric-value">
                        {opt.transit_days} {opt.transit_days === 1 ? 'business day' : 'business days'}
                      </strong>
                    </div>

                    <div className="cw-transport-metric">
                      <span className="cw-metric-label">Estimated Delivery (ETA)</span>
                      <strong className="cw-metric-value cw-val--eta">
                        {new Date(opt.estimated_delivery_date).toLocaleDateString('en-GB', {
                          weekday: 'short',
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </strong>
                    </div>


                  <div className="cw-transport-footer">
                    <div className="cw-transport-price">
                      <span className="cw-price-label">Estimated Freight Cost</span>
                      <strong className="cw-price-value">
                        €{opt.total_cost.toFixed(2)} <small>{opt.currency}</small>
                      </strong>
                    </div>

                    <button
                      type="button"
                      className={`cw-btn cw-btn--select${isSelected ? ' is-selected' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectOption(opt)
                      }}
                    >
                      {isSelected ? '✓ Selected' : 'Select Mode'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      <div className="cw-actions">
        <button type="button" className="cw-btn cw-btn--secondary" onClick={onBack}>
          ← Back to Stock
        </button>
        <button
          type="button"
          className="cw-btn cw-btn--primary"
          onClick={onNext}
          disabled={!selectedOptionId}
        >
          Next: Order Review →
        </button>
      </div>
    </div>
  )
}
