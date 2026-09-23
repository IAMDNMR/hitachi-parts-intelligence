import type { ReactNode, SVGProps } from 'react'

/**
 * Line icons for Section 03.
 *
 * Ten attribute marks plus four interface marks — nothing else. The
 * attribute vocabulary in data/partsCatalogue.ts's partAttributes is small
 * on purpose, and this file stays the same size as that vocabulary (the
 * five added alongside PT-044..048 brought it from five marks to ten).
 *
 * Same language as the rest of the site: a 24px grid, one stroke weight,
 * round joins, no fills.
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
  // Genuine OEM — a shield with a check
  genuine: (
    <>
      <path d="M12 3l7 2.8v6c0 4.6-3 7.8-7 9.2-4-1.4-7-4.6-7-9.2v-6z" />
      <path d="M8.6 12.2l2.4 2.4 4.4-4.8" />
    </>
  ),
  // Heavy-duty — a loaded weight bar
  heavyduty: (
    <>
      <rect x="4" y="9" width="3" height="6" rx="0.8" />
      <rect x="17" y="9" width="3" height="6" rx="0.8" />
      <path d="M7 12h10" />
      <rect x="9.5" y="7" width="5" height="10" rx="0.8" />
    </>
  ),
  // High-pressure — a gauge with the needle up
  highpressure: (
    <>
      <circle cx="12" cy="13" r="7.5" />
      <path d="M12 13l3-4.5" />
      <path d="M12 5.5v1.2M5.6 9.5l1 .6M18.4 9.5l-1 .6" />
    </>
  ),
  // High-torque — rotational force around a shaft
  hightorque: (
    <>
      <circle cx="12" cy="12" r="2" />
      <path d="M12 4.5a7.5 7.5 0 0 1 6.5 3.75" />
      <path d="M12 19.5a7.5 7.5 0 0 1-6.5-3.75" />
      <path d="M17.2 6.6l1.8 1.65-2.35.85M6.8 17.4l-1.8-1.65 2.35-.85" />
    </>
  ),
  // Precision-engineered — a crosshair
  precision: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="12" cy="12" r="2.4" />
      <path d="M12 2.8v3M12 18.2v3M2.8 12h3M18.2 12h3" />
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

export function PartIcon({ name, size = 20 }: { name: string; size?: number }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
