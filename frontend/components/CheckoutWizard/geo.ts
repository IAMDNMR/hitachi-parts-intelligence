/**
 * European Depot & Haversine Distance Utilities
 */

export const OOSTERHOUT_DEPOT = {
  id: 'DEPOT-OOSTERHOUT',
  name: 'Hitachi European Parts Centre',
  city: 'Oosterhout',
  country: 'NL',
  latitude: 51.6431,
  longitude: 4.8569,
}

/**
 * Calculates Great-Circle straight-line distance in km between two coordinate pairs using Haversine formula.
 */
export function calculateHaversineKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371.0
  const dLat = ((lat2 - lat1) * Math.PI) / 180.0
  const dLon = ((lon2 - lon1) * Math.PI) / 180.0
  const radLat1 = (lat1 * Math.PI) / 180.0
  const radLat2 = (lat2 * Math.PI) / 180.0

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(radLat1) * Math.cos(radLat2) * Math.sin(dLon / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return Math.round(R * c * 100) / 100
}

/**
 * Estimates road transport distance using European routing factor 1.25x.
 */
export function estimateRoadKm(straightLineKm: number): number {
  return Math.round(straightLineKm * 1.25 * 100) / 100
}
