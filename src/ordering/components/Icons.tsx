/**
 * A small, deliberately plain icon set.
 *
 * Drawn here rather than pulled from a library: five 16px glyphs do not
 * justify a dependency, and an icon font would arrive as a second typeface
 * on a site that has one. All of them inherit `currentColor` and sit on the
 * same 16-unit grid with the same 1.5 stroke, so they read as one family
 * next to the interface type rather than as clip art.
 */
const base = {
  width: 16,
  height: 16,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

export const IconList = () => (
  <svg {...base}>
    <path d="M5.5 4h8M5.5 8h8M5.5 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01" />
  </svg>
)

/** An excavator, reduced to the silhouette that reads at 16px: tracks, a
 *  body and a boom. The machine is the anchor of this application, so it
 *  gets a shape of its own rather than a generic box. */
export const IconMachine = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
    strokeLinecap="round" strokeLinejoin="round" width="18" height="18" aria-hidden="true">
    <rect x="3" y="14" width="12" height="4" rx="2" />
    <rect x="6" y="9" width="7" height="5" rx="1" />
    <path d="M13 10 L18 5 L21 8" />
    <path d="M21 8 L20 12" />
  </svg>
)

export const IconParts = () => (
  <svg {...base}>
    <path d="M8 1.8 14 5v6l-6 3.2L2 11V5z" />
    <path d="M2 5l6 3.2L14 5M8 8.2v6" />
  </svg>
)

export const IconEdit = () => (
  <svg {...base}>
    <path d="M11.2 2.6a1.7 1.7 0 0 1 2.4 2.4L5.5 13 2 14l1-3.5z" />
  </svg>
)

export const IconTrash = () => (
  <svg {...base}>
    <path d="M2.5 4h11M6 4V2.5h4V4M12.5 4l-.6 9a1 1 0 0 1-1 1h-5.8a1 1 0 0 1-1-1L3.5 4M6.5 7v4M9.5 7v4" />
  </svg>
)

export const IconPlus = () => (
  <svg {...base}>
    <path d="M8 3v10M3 8h10" />
  </svg>
)

export const IconMinus = () => (
  <svg {...base}>
    <path d="M3 8h10" />
  </svg>
)

export const IconBack = () => (
  <svg {...base}>
    <path d="M13 8H3M7 4 3 8l4 4" />
  </svg>
)

export const IconSearch = () => (
  <svg {...base}>
    <circle cx="7" cy="7" r="4.5" />
    <path d="m10.5 10.5 3 3" />
  </svg>
)

export const IconHome = () => (
  <svg {...base}>
    <path d="M2.5 7 8 2.5 13.5 7v6a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1z" />
    <path d="M6.5 14V9.5h3V14" />
  </svg>
)

export const IconDoc = () => (
  <svg {...base}>
    <path d="M4 2h5l3 3v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z" />
    <path d="M9 2v3h3M5.5 8.5h5M5.5 11h5" />
  </svg>
)

export const IconHourglass = () => (
  <svg {...base}>
    <path d="M4 2h8M4 14h8M5 2v2.5L8 8l3-3.5V2M5 14v-2.5L8 8l3 3.5V14" />
  </svg>
)

export const IconTruck = () => (
  <svg {...base}>
    <path d="M1.5 4.5h8v6h-8zM9.5 7h2.7l1.8 2v1.5h-4.5z" />
    <circle cx="4.5" cy="12" r="1.3" />
    <circle cx="11.5" cy="12" r="1.3" />
  </svg>
)

export const IconCheckCircle = () => (
  <svg {...base}>
    <circle cx="8" cy="8" r="6" />
    <path d="m5.5 8 1.8 1.8L10.5 6.5" />
  </svg>
)

export const IconFilter = () => (
  <svg {...base}>
    <path d="M2 3.5h12L9.5 8.7V13L6.5 11.5V8.7z" />
  </svg>
)

export const IconChevronRight = () => (
  <svg {...base}>
    <path d="m6 3 5 5-5 5" />
  </svg>
)

export const IconChevronLeft = () => (
  <svg {...base}>
    <path d="m10 3-5 5 5 5" />
  </svg>
)

export const IconChevronDown = () => (
  <svg {...base}>
    <path d="m3 6 5 5 5-5" />
  </svg>
)

export const IconDots = () => (
  <svg {...base}>
    <circle cx="8" cy="3" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="8" cy="8" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="8" cy="13" r="1.1" fill="currentColor" stroke="none" />
  </svg>
)

export const IconChart = () => (
  <svg {...base}>
    <path d="M2.5 13.5V9M6.5 13.5V4M10.5 13.5v-6M14 13.5V2.5" />
  </svg>
)

export const IconEye = () => (
  <svg {...base}>
    <path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z" />
    <circle cx="8" cy="8" r="2" />
  </svg>
)

export const IconGear = () => (
  <svg {...base}>
    <circle cx="8" cy="8" r="2.4" />
    <path d="M8 1.5v1.6M8 12.9v1.6M2.9 2.9l1.2 1.2M11.9 11.9l1.2 1.2M1.5 8h1.6M12.9 8h1.6M2.9 13.1l1.2-1.2M11.9 4.1l1.2-1.2" />
  </svg>
)

export const IconWrench = () => (
  <svg {...base}>
    <path d="M10.6 2.2a3.4 3.4 0 0 0-4 4.4L2.6 10.6a1.4 1.4 0 0 0 2 2l4-4a3.4 3.4 0 0 0 4.4-4l-2 2-1.4-1.4z" />
  </svg>
)

export const IconEngine = () => (
  <svg {...base}>
    <path d="M2 6.5h2l1.5-2h4L11 6.5h3v5h-2.5l-1.5 2h-4L4.5 11.5H2z" />
    <path d="M6 2.5h4" />
  </svg>
)

export const IconMore = () => (
  <svg {...base}>
    <circle cx="3.2" cy="8" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="8" cy="8" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="12.8" cy="8" r="1.1" fill="currentColor" stroke="none" />
  </svg>
)

export const IconCart = () => (
  <svg {...base}>
    <path d="M1.5 2h1.8l1.6 7.4h6.4l1.7-5.2H4.2" />
    <circle cx="6" cy="13" r="1.1" />
    <circle cx="11" cy="13" r="1.1" />
  </svg>
)

export const IconCopy = () => (
  <svg {...base}>
    <rect x="5.5" y="5.5" width="8" height="8" rx="1.2" />
    <path d="M10.5 5.5v-2a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2" />
  </svg>
)
