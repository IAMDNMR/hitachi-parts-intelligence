/**
 * Pure helper for converging a Parts Intelligence candidate onto the same
 * canonical Part selection path the normal catalogue uses. Extracted so it
 * can be unit tested without a React rendering harness.
 */
export interface CataloguePartLike {
  id: string
  partNumber?: string | null
}

/** Returns the catalogue product id whose partNumber exactly matches, or
 * null if this Part is not present in the current catalogue view (the
 * caller should then fall back to the normal search box with this part
 * number, never invent a product record). */
export function findCatalogueMatchId(products: CataloguePartLike[], partNumber: string | null | undefined): string | null {
  if (!partNumber) return null
  const match = products.find((p) => p.partNumber === partNumber)
  return match ? match.id : null
}
