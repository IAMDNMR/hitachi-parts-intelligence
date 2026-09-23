import type { ReactNode, SVGProps } from 'react'

/**
 * Line icons for Section 04.
 *
 * Five stage marks and two capability marks — the size of the vocabulary the
 * section actually names, and nothing beyond it. The generated sphere and
 * node-graph graphics that used to sit beside ConSite and Global e-Service
 * are gone: at the size they were drawn they were decoration, and this
 * section is meant to read as precision rather than complexity.
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
  // Inspect — look closely before touching anything
  inspect: (
    <>
      <circle cx="10.6" cy="10.6" r="6.6" />
      <path d="M15.4 15.4L20.5 20.5" />
      <path d="M8.2 10.6h4.8M10.6 8.2v4.8" />
    </>
  ),
  // Diagnose — read what the machine reports
  diagnose: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M6.4 12h2.4l1.5-3.6 2.4 7.2 1.5-3.6h2.6" />
    </>
  ),
  // Maintain — planned work
  maintain: (
    <path d="M15.5 3.5a4.5 4.5 0 0 0-5.9 5.9L3 16v5h5l6.6-6.6a4.5 4.5 0 0 0 5.9-5.9l-3 3-2.9-.6-.6-2.9z" />
  ),
  // Repair — the part goes back in
  repair: (
    <>
      <path d="M12 2.9l7.9 4.55v9.1L12 21.1 4.1 16.55v-9.1z" />
      <circle cx="12" cy="12" r="3.1" />
    </>
  ),
  // Back to work
  uptime: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M10.2 8.6l6 3.4-6 3.4z" />
    </>
  ),

  // --- capabilities ------------------------------------------------------
  // ConSite — the machine reporting its condition
  consite: (
    <>
      <circle cx="12" cy="17.6" r="1.7" />
      <path d="M8.1 14.5a5.5 5.5 0 0 1 7.8 0" />
      <path d="M5.2 11.1a9.6 9.6 0 0 1 13.6 0" />
    </>
  ),
  // Global e-Service — support wherever the machine is
  globalservice: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M3.5 12h17" />
      <path d="M12 3.5c2.3 2.4 3.4 5.3 3.4 8.5S14.3 18.1 12 20.5c-2.3-2.4-3.4-5.3-3.4-8.5S9.7 5.9 12 3.5z" />
    </>
  ),

  mouse: (
    <>
      <rect x="8" y="2.8" width="8" height="14" rx="4" />
      <path d="M12 6.2v2.6" />
      <path d="M12 19v2.4M10.4 20.4L12 22l1.6-1.6" />
    </>
  ),
}

export function ServiceIcon({ name, size = 20 }: { name: string; size?: number }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
