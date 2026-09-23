import type { ReactNode, SVGProps } from 'react'

/**
 * Marks for Section 05 — three pillars and two arrows, nothing else.
 *
 * Same language as the rest of the site: a 24px grid, one stroke weight,
 * round joins, no fills.
 */
const common: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.3,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

const paths: Record<string, ReactNode> = {
  // Parts — a spanner
  parts: (
    <path d="M15.5 3.5a4.5 4.5 0 0 0-5.9 5.9L3 16v5h5l6.6-6.6a4.5 4.5 0 0 0 5.9-5.9l-3 3-2.9-.6-.6-2.9z" />
  ),
  // Service — the person who does the work
  service: (
    <>
      <path d="M6.6 10.2a5.4 5.4 0 0 1 10.8 0" />
      <path d="M5.2 10.2h13.6" />
      <path d="M4.2 20.8v-1.5c0-2.1 2.3-3.3 5.3-3.8M19.8 20.8v-1.5c0-2.1-2.3-3.3-5.3-3.8" />
      <path d="M9.6 13.2a3.5 3.5 0 0 0 4.8 0" />
    </>
  ),
  // Data — readings over time
  data: (
    <>
      <path d="M4 20h16" />
      <path d="M7.5 20V10M12 20V4.8M16.5 20v-6.4" />
    </>
  ),
  arrow: <path d="M4.5 12h15M14 6.5l5.5 5.5L14 17.5" />,
  arrowUp: <path d="M12 19.5v-15M5.5 11L12 4.5 18.5 11" />,
}

export function UptimeIcon({ name, size = 22 }: { name: string; size?: number }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
