import type { ReactNode, SVGProps } from 'react'

/**
 * Line icons for the Parts Store's Quick View "Key Information" panel.
 *
 * Same language as sections/PartsShowcase/PartIcons.jsx (24px grid, one
 * stroke weight, round joins, no fills) but a separate, smaller vocabulary
 * — these six marks are specific to the facts this panel always shows
 * (category, part number, compatibility, relationship level, availability,
 * price), plus one for the help callout. Kept apart from PartIcons.jsx
 * rather than folded in, since that file is deliberately sized to its own
 * (attribute) vocabulary.
 */
const common: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.25,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

const paths: Record<string, ReactNode> = {
  // Category — a 2x2 grid
  category: (
    <>
      <rect x="3.5" y="3.5" width="7.2" height="7.2" rx="1.2" />
      <rect x="13.3" y="3.5" width="7.2" height="7.2" rx="1.2" />
      <rect x="3.5" y="13.3" width="7.2" height="7.2" rx="1.2" />
      <rect x="13.3" y="13.3" width="7.2" height="7.2" rx="1.2" />
    </>
  ),
  // Part number — a barcode
  partNumber: (
    <>
      <path d="M4 4.5v15" />
      <path d="M7.5 4.5v15" />
      <path d="M10 4.5v15" />
      <path d="M13.5 4.5v15" />
      <path d="M16 4.5v15" />
      <path d="M20 4.5v15" />
    </>
  ),
  // Compatibility — a machine (excavator-like silhouette)
  compatibility: (
    <>
      <path d="M3 18.5h10" />
      <path d="M4.5 18.5v-4.2l3.4-2.4h3.6l2 2.4" />
      <path d="M11.5 8.5l4.5-3.6 1.8 1.4-3 4.2 2.2 2.6-2.4 5.4" />
      <circle cx="6.2" cy="18.5" r="1.6" />
      <circle cx="14.5" cy="18.5" r="1.6" />
    </>
  ),
  // Relationship level — a link
  relationship: (
    <>
      <path d="M9.5 14.5l5-5" />
      <path d="M8 10.5L5.6 12.9a3 3 0 0 0 4.24 4.24L12.3 14.7" />
      <path d="M16 13.5l2.4-2.4a3 3 0 0 0-4.24-4.24L11.7 9.3" />
    </>
  ),
  // Availability — a package
  availability: (
    <>
      <path d="M12 3.5l8 4v9l-8 4-8-4v-9z" />
      <path d="M4 7.5l8 4 8-4M12 11.5v9" />
    </>
  ),
  // Price — stacked coins
  price: (
    <>
      <ellipse cx="12" cy="6.2" rx="6.4" ry="2.6" />
      <path d="M5.6 6.2v5.4c0 1.4 2.9 2.6 6.4 2.6s6.4-1.2 6.4-2.6V6.2" />
      <path d="M5.6 11.6V17c0 1.4 2.9 2.6 6.4 2.6s6.4-1.2 6.4-2.6v-5.4" />
    </>
  ),
  // Help — an info mark
  help: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5" />
      <circle cx="12" cy="8" r="0.15" fill="currentColor" stroke="none" />
    </>
  ),
  // Provenance warning — a triangle alert, distinct from the info/category
  // marks so an unverified-provenance fact doesn't read as an ordinary spec.
  warning: (
    <>
      <path d="M12 3.8l9 15.6H3z" />
      <path d="M12 10v4.2" />
      <circle cx="12" cy="16.8" r="0.15" fill="currentColor" stroke="none" />
    </>
  ),
}

export function DetailIcon({ name, size = 20 }: { name: string; size?: number }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
