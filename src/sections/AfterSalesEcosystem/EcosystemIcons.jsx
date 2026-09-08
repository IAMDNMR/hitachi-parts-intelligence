/**
 * The four state marks for Section 02.
 *
 * Same language as the rest of the site: a 24px grid, one stroke weight,
 * round joins, no fills, no gradients, no glow. One mark per state and
 * nothing else — the section names four ideas, so it needs four icons.
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
  // Machine data — readings over time
  data: (
    <>
      <path d="M4 20h16" />
      <path d="M7 20V9.5M12 20V4.5M17 20v-7" />
    </>
  ),
  // Parts — a component in exploded view
  parts: (
    <>
      <path d="M12 3l8 3.6v8.8L12 21l-8-5.6V6.6z" />
      <path d="M4 6.6l8 3.6 8-3.6M12 10.2V21" />
    </>
  ),
  // Service — a spanner
  service: (
    <path d="M15.5 3.5a4.5 4.5 0 0 0-5.9 5.9L3 16v5h5l6.6-6.6a4.5 4.5 0 0 0 5.9-5.9l-3 3-2.9-.6-.6-2.9z" />
  ),
  // Network — people and places connected
  network: (
    <>
      <circle cx="12" cy="5" r="2.2" />
      <circle cx="5" cy="18" r="2.2" />
      <circle cx="19" cy="18" r="2.2" />
      <path d="M10.6 6.9L6.4 16.1M13.4 6.9l4.2 9.2M7.2 18h9.6" />
    </>
  ),
}

export function EcoIcon({ name, size = 20 }) {
  const path = paths[name]
  if (!path) return null
  return (
    <svg {...common} width={size} height={size}>
      {path}
    </svg>
  )
}
