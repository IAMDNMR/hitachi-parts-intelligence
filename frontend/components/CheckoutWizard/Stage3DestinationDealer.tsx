import { useState, useMemo } from 'react'
import type { DealerOption } from '../../types/api'
import { OOSTERHOUT_DEPOT, calculateHaversineKm, estimateRoadKm } from './geo'

interface Stage3DestinationDealerProps {
  dealers: DealerOption[]
  selectedDealerId: string
  onSelectDealer: (dealer: DealerOption) => void
  onBack: () => void
  onNext: () => void
}

export default function Stage3DestinationDealer({
  dealers,
  selectedDealerId,
  onSelectDealer,
  onBack,
  onNext,
}: Stage3DestinationDealerProps) {
  const [searchQuery, setSearchQuery] = useState('')

  // Compute straight-line distance for each dealer with coordinates
  const enrichedDealers = useMemo(() => {
    return dealers.map((d) => {
      let distanceKm: number | null = null
      if (d.latitude != null && d.longitude != null) {
        distanceKm = calculateHaversineKm(
          OOSTERHOUT_DEPOT.latitude,
          OOSTERHOUT_DEPOT.longitude,
          d.latitude,
          d.longitude
        )
      }
      return { ...d, distance_km: distanceKm }
    })
  }, [dealers])

  const selectedDealer = useMemo(() => {
    return enrichedDealers.find((d) => d.dealer_id === selectedDealerId) || null
  }, [enrichedDealers, selectedDealerId])

  const filteredDealers = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return enrichedDealers
    return enrichedDealers.filter(
      (d) =>
        d.dealer_name.toLowerCase().includes(q) ||
        (d.city && d.city.toLowerCase().includes(q)) ||
        d.country.toLowerCase().includes(q) ||
        d.dealer_id.toLowerCase().includes(q) ||
        (d.address && d.address.toLowerCase().includes(q))
    )
  }, [enrichedDealers, searchQuery])

  const dealersByCountry = useMemo(() => {
    const map = new Map<string, typeof enrichedDealers>()
    for (const d of filteredDealers) {
      const c = d.country || 'Other'
      map.set(c, [...(map.get(c) ?? []), d])
    }
    // Sort countries alphabetically
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [filteredDealers])

  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--real">REAL · HCME EUROPEAN DEALER NETWORK</div>
        <h3 className="cw-stage__title">3. Destination Dealer Selection</h3>
        <p className="cw-stage__desc">
          Select a verified European dealer branch from the public HCME dealer feed (181 of 182 branches mapped with
          GPS coordinates). Distances are computed directly from the European Parts Centre in Oosterhout, Netherlands.
        </p>
      </div>

      <div className="cw-field">
        <label htmlFor="dealer-search">Search European Dealer Branches ({dealers.length} locations · 181 with GPS)</label>
        <div className="cw-search-input-wrapper">
          <input
            id="dealer-search"
            type="text"
            placeholder="Search by dealer name, city, country, or code (e.g. Auer, Matrei, AT)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="cw-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="cw-field">
        <label htmlFor="dealer-select">Select Branch</label>
        <select
          id="dealer-select"
          value={selectedDealerId}
          onChange={(e) => {
            const found = enrichedDealers.find((d) => d.dealer_id === e.target.value)
            if (found) onSelectDealer(found)
          }}
          className="cw-select"
          size={5}
        >
          {dealersByCountry.map(([country, branchList]) => (
            <optgroup key={country} label={`${country} (${branchList.length} branches)`}>
              {branchList.map((d) => (
                <option key={d.dealer_id} value={d.dealer_id}>
                  {d.dealer_name} {d.city ? `· ${d.city}` : ''} ({d.dealer_id})
                  {d.distance_km != null ? ` — ${d.distance_km} km` : ' — GPS pending'}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {selectedDealer && (
        <div className="cw-card cw-card--dealer">
          <div className="cw-card__dealer-head">
            <div>
              <span className="cw-tag cw-tag--blue">SELECTED DESTINATION BRANCH</span>
              <h4 className="cw-card__dealer-title">{selectedDealer.dealer_name}</h4>
              <p className="cw-card__dealer-sub">
                Branch ID: <code>{selectedDealer.dealer_id}</code> · Country: <strong>{selectedDealer.country}</strong>
                {selectedDealer.city && ` · City: ${selectedDealer.city}`}
              </p>
            </div>
            {selectedDealer.distance_km != null && (
              <div className="cw-distance-badge">
                <span className="cw-distance-badge__val">{selectedDealer.distance_km} km</span>
                <span className="cw-distance-badge__label">Straight-Line</span>
              </div>
            )}
          </div>

          <div className="cw-specs-grid" style={{ marginTop: '0.8rem' }}>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Address</span>
              <strong className="cw-spec-item__val">{selectedDealer.address || 'Standard European Branch Depot'}</strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">GPS Coordinates</span>
              <strong className="cw-spec-item__val cw-val--real">
                {selectedDealer.latitude != null && selectedDealer.longitude != null
                  ? `${selectedDealer.latitude.toFixed(4)}°N, ${selectedDealer.longitude.toFixed(4)}°E`
                  : 'Coordinates not mapped (181 of 182 branches mapped)'}
              </strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Straight-Line Distance</span>
              <strong className="cw-spec-item__val cw-val--derived">
                {selectedDealer.distance_km != null ? `${selectedDealer.distance_km} km` : 'Calculated via Haversine (GPS pending)'}
              </strong>
            </div>
            <div className="cw-spec-item">
              <span className="cw-spec-item__label">Estimated Road Distance</span>
              <strong className="cw-spec-item__val cw-val--derived">
                {selectedDealer.distance_km != null
                  ? `~${estimateRoadKm(selectedDealer.distance_km)} km (1.25×)`
                  : 'Road factor applied'}
              </strong>
            </div>
          </div>

          <div className="cw-provenance-bar">
            <span>
              <strong>REAL:</strong> 182 verified European dealer branches from public HCME dealer feed (181 with GPS coordinates).
            </span>
            <span>
              <strong>DERIVED:</strong> Straight-line Great-Circle distance from Oosterhout (51.6431°N, 4.8569°E).
            </span>
          </div>
        </div>
      )}

      <div className="cw-actions">
        <button type="button" className="cw-btn cw-btn--secondary" onClick={onBack}>
          ← Back to Requester
        </button>
        <button
          type="button"
          className="cw-btn cw-btn--primary"
          onClick={onNext}
          disabled={!selectedDealerId}
        >
          Check Stock &amp; Availability →
        </button>
      </div>
    </div>
  )
}
