/**
 * Section 05 — the close.
 *
 * The three pillars restate what the preceding sections built, in one line
 * each: parts (03), service (04) and the machine data the ecosystem (02)
 * runs on. Nothing new is introduced here and nothing is quantified — this
 * section closes the argument rather than making a fresh one.
 */
export const uptimePillars = [
  {
    id: 'parts',
    icon: 'parts',
    title: 'Parts',
    lines: ['Genuine parts,', 'engineered reliability.'],
  },
  {
    id: 'service',
    icon: 'service',
    title: 'Service',
    lines: ['Expert support,', 'wherever you are.'],
  },
  {
    id: 'data',
    icon: 'data',
    title: 'Data',
    lines: ['Smart insights,', 'better decisions.'],
  },
]

/**
 * The five chapters, for the rail on the outer edge. This is the last of
 * them, so the rail is a position indicator rather than a control — the
 * page is scrolled, not navigated.
 */
export const chapters = ['The machine', 'Ecosystem', 'Parts', 'Service', 'Uptime']

/**
 * Where the footer can take you.
 *
 * This was Privacy Policy / Terms of Use / Cookies / Sitemap — four inert
 * spans, honestly commented as placeholders in the source and indistinguishable
 * from broken links on the screen. None of those pages exist in this project
 * and none of them is what a reader wants at this point anyway.
 *
 * What they want is the two things this project actually built. The header
 * offers both, and the header is five full sections of scrolling behind them
 * by the time they reach here — so the end of the page is exactly where the
 * offer is worth repeating.
 *
 * `to` is read by SiteFooter: 'ground' and 'ordering' open those routes,
 * 'top' returns to the start of the story.
 */
export const footerLinks = [
  { label: 'The Ground', to: 'ground' },
  { label: 'Parts Ordering', to: 'ordering' },
  { label: 'Back to the top', to: 'top' },
]
