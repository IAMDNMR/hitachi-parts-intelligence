/**
 * Thin line icons for the ecosystem nodes. Deliberately geometric and
 * single-weight — no fills, no gradients, no glow.
 */
const common = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.3,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

const paths = {
  // Parts — a component / box in exploded view
  parts: (
    <>
      <path d="M12 3 20 7v10l-8 4-8-4V7z" />
      <path d="M4 7l8 4 8-4M12 11v10" />
    </>
  ),
  // Service — spanner
  service: (
    <>
      <path d="M15.5 3.5a4.5 4.5 0 0 0-5.9 5.9L3 16v5h5l6.6-6.6a4.5 4.5 0 0 0 5.9-5.9l-3 3-2.9-.6-.6-2.9z" />
    </>
  ),
  // Dealer network — connected locations
  network: (
    <>
      <circle cx="5" cy="6" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="12" cy="18" r="2" />
      <path d="M6.6 7.4 10.6 16.4M17.4 7.4 13.4 16.4M7 6h10" />
    </>
  ),
  // Warranty — shield with a check
  warranty: (
    <>
      <path d="M12 3l7 3v6c0 4-3 7.4-7 9-4-1.6-7-5-7-9V6z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  // Logistics — delivery vehicle
  logistics: (
    <>
      <path d="M2 7h11v9H2zM13 10h4l3 3v3h-7z" />
      <circle cx="6.5" cy="18" r="1.6" />
      <circle cx="17" cy="18" r="1.6" />
    </>
  ),
  // Machine data — signal over a baseline
  data: (
    <>
      <path d="M3 20h18" />
      <path d="M6 16V9M11 16V5M16 16v-5M21 16v-8" />
    </>
  ),
}

export function NodeIcon({ name }) {
  return <svg {...common}>{paths[name] ?? paths.parts}</svg>
}

export function ArrowRight() {
  return (
    <svg
      className="cta__arrow"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 12h15M13 6l6 6-6 6" />
    </svg>
  )
}

export function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}
