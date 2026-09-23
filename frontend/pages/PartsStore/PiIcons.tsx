/** Small stroke icon set for Parts Intelligence (24px grid, currentColor). */

const PATHS = {
  graph: 'M6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm12 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm-1 0-4 7m6-7 4 7M8 17h8',
  truck: 'M3 7h11v9H3zM14 10h4l3 3v3h-7M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  shield: 'M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z',
  factory: 'M3 21V10l6 4V10l6 4V6l6 3v12H3Zm4-4h2m4 0h2',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  alert: 'M12 3 2 21h20L12 3Zm0 7v5m0 3h.01',
  layers: 'm12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5',
  info: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-11v6m0-9h.01',
  check: 'M4 12l5 5L20 6',
  x: 'M6 6l12 12M18 6 6 18',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-15v5l3 3',
  send: 'M21 3 10 14M21 3l-7 18-4-7-7-4 18-7Z',
  chevron: 'm6 9 6 6 6-6',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm10 2-4.35-4.35',
  pin: 'M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12Zm0-9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  hash: 'M4 9h16M4 15h16M10 3 8 21M16 3l-2 18',
  tag: 'M3 12V3h9l9 9-9 9-9-9Zm5-4h.01',
  cog: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2-1.2L14.5 3h-5l-.4 2.6a7 7 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 2 1.2l.4 2.6h5l.4-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2Z',
  spark: 'M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5m7 7L18 18M18 6l-2.5 2.5m-7 7L6 18',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  message: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  plug: 'M12 2v6m-4-6v6m-2 4h12v3a6 6 0 0 1-12 0v-3Zm6 9v3',
  car: 'M5 17h14M6 17l1.5-6h9L18 17M6 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm16 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM4 11h16',
  swap: 'm16 3 4 4-4 4M20 7H4m4 14-4-4 4-4M4 17h16',
  sparkles: 'm12 3 1.9 4.5L18.4 9.4l-4.5 1.9L12 15.8l-1.9-4.5L5.6 9.4l4.5-1.9L12 3Zm7 13 1 2.3 2.3 1-2.3 1-1 2.3-1-2.3-2.3-1 2.3-1 1-2.3Z',
} as const

export type PiIconName = keyof typeof PATHS

export function PiIcon({ name, size = 18 }: { name: PiIconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="pix-icon"
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
