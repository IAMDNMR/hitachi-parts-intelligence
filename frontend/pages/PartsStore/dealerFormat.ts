/**
 * Tidy dealer text for display only (the stored data is untouched). The dealer-locator feed has ALL-CAPS names/addresses, a street repeated
 * inside the address, and some entries without a city.
 */

const KEEP_UPPER = new Set(['GMBH', 'BV', 'NV', 'KG', 'GBR', 'AG', 'SA', 'SRL', 'SPA', 'OY', 'AB', 'AS', 'UG', 'LTD', 'LLC', 'EK', 'E.K.', 'CO.', 'S.A.', 'N.V.', 'B.V.'])
const SPECIAL: Record<string, string> = { GMBH: 'GmbH', 'E.K.': 'e.K.', EK: 'e.K.' }

const titleWord = (w: string): string => {
  const up = w.toUpperCase()
  if (SPECIAL[up]) return SPECIAL[up]
  if (KEEP_UPPER.has(up)) return up
  return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
}

/** "SCHWAB GMBH" -> "Schwab GmbH"; text that already has lower-case letters is left alone. */
export function tidyCase(text: string | null | undefined): string {
  const t = (text ?? '').trim()
  if (!t || t !== t.toUpperCase() || !/[A-ZÀ-Þ]/.test(t)) return t
  return t.replace(/[^\s,/-]+/g, titleWord)
}

/** "KUCHENGRUND 21, KUCHENGRUND 21 BACKNANG" -> "Kuchengrund 21, Backnang" (a segment that just repeats the previous one is dropped). */
export function tidyAddress(address: string | null | undefined): string {
  const segs = (address ?? '').split(',').map((s) => s.trim()).filter(Boolean)
  const out: string[] = []
  for (const seg of segs) {
    const prev = out[out.length - 1]
    if (prev && seg.toLowerCase().startsWith(prev.toLowerCase())) {
      const rest = seg.slice(prev.length).trim()
      if (rest) out.push(rest)
    } else {
      out.push(seg)
    }
  }
  return tidyCase(out.join(', '))
}

/** The city, or - when the feed left it empty - the place name that follows the postcode in the address. */
export function dealerCity(city: string | null | undefined, address: string | null | undefined): string {
  const c = (city ?? '').trim()
  if (c) return tidyCase(c)
  const m = (address ?? '').match(/\b\d{4,5}(?:\s?[A-Z]{2})?,?\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]*?)\s*(?:,|$)/)
  return m?.[1] ? tidyCase(m[1]) : ''
}
