import type { OrderResult } from '../types/api'

/**
 * Pure display-formatting helper for the Order review step (Phase 6).
 *
 * Never fabricates a price: if the backend's pricingStatus is anything
 * other than CONFIRMED, or unitPrice is null/undefined, this always
 * returns the honest "Price unavailable from current source" label rather
 * than showing 0, blank, or any invented number.
 */
export function formatOrderPrice(
  order: Pick<OrderResult, 'unitPrice' | 'currency' | 'pricingStatus'>
): string {
  if (order.pricingStatus !== 'CONFIRMED' || order.unitPrice == null) {
    return 'Price unavailable from current source'
  }
  return `${order.unitPrice} ${order.currency ?? ''}`.trim()
}
