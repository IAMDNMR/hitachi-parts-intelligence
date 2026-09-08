/**
 * Line icons for Section 03.
 *
 * Five attribute marks plus four interface marks — nothing else. The
 * attribute vocabulary in data/partsCatalogue.js is small on purpose, and
 * this file stays the same size as that vocabulary.
 *
 * Same language as the rest of the site: a 24px grid, one stroke weight,
 * round joins, no fills.
 */
const common = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.25,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

const paths = {
  // Exact fit — two halves meeting on one line
  exactfit: (
    <>
      <path d="M12 2.8v18.4" />
      <path d="M8.6 6.4H4.2v11.2h4.4" />
      <path d="M15.4 6.4h4.4v11.2h-4.4" />
      <path d="M8.6 12h1.6M13.8 12h1.6" />
    </>
  ),
  // Reliable — it holds its line
  reliable: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M6.6 12.4h2.6l1.6-3.2 2.4 6 1.6-3.2h2.6" />
    </>
  ),
  // Durable — layered, wear-resistant
  durable: (
    <>
      <path d="M3.5 8.5L12 4.5l8.5 4-8.5 4z" />
      <path d="M3.5 12.5L12 16.5l8.5-4" />
      <path d="M3.5 16L12 20l8.5-4" />
    </>
  ),
  // Serviceable — it can be maintained in the field
  serviceable: (
    <path d="M15.5 3.5a4.5 4.5 0 0 0-5.9 5.9L3 16v5h5l6.6-6.6a4.5 4.5 0 0 0 5.9-5.9l-3 3-2.9-.6-.6-2.9z" />
  ),
  // Available — it can be got hold of
  available: (
    <>
      <path d="M9.5 4.5l6 2.7v6.6l-6 2.7-6-2.7V7.2z" />
      <path d="M3.5 7.2l6 2.7 6-2.7M9.5 9.9v6.6" />
      <path d="M14 19.5h7M18 16.5l3 3-3 3" />
    </>
  ),

  // --- interface ---------------------------------------------------------
  // Category mark
  tag: (
    <>
      <circle cx="12" cy="12" r="7.6" />
      <circle cx="12" cy="12" r="2.2" />
    </>
  ),
  // 360° view
  orbit: (
    <>
      <ellipse cx="12" cy="12" rx="9.4" ry="4.4" />
      <circle cx="12" cy="12" r="2.4" />
      <path d="M12 6.2v-2M12 19.8v-2" />
    </>
  ),
  mouse: (
    <>
      <rect x="8" y="2.8" width="8" height="14" rx="4" />
      <path d="M12 6.2v2.6" />
      <path d="M12 19v2.4M10.4 20.4L12 22l1.6-1.6" />
    </>
  ),
  arrow: <path d="M4.5 12h15M14 6.5l5.5 5.5L14 17.5" />,
}

export function PartIcon({ name, size = 20 }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
