/**
 * Story configuration for the hero.
 *
 * The viewport is treated as one composition, not a text column beside a
 * video. Each state therefore carries a `layout`: where its label, headline,
 * note and call to action sit as percentages of the viewport, and how large
 * the headline is. Those positions are art direction — they are chosen
 * against the machine's silhouette at that point in the clip, so type crosses
 * the machine's axis and sinks into its dark components rather than sitting
 * politely beside it.
 *
 *   x      percentage of the viewport width, from the left
 *   y      percentage of the viewport height, from the top — or, when
 *          `below` is set, an offset in vh measured from under the header,
 *          which is what the top-band placements need: the header is a fixed
 *          pixel height, so a raw percentage collides with it on short
 *          viewports and floats away from it on tall ones
 *   size   headline size in vw
 *   anchor 'left' or 'right' — which edge of the text block x refers to
 *
 * Everything is driven by `progress`, a normalised 0..1 value derived from
 * scroll position. Nothing is tied to pixel offsets, so re-timing or
 * recomposing the story means editing this file and nothing else.
 */

interface LayoutSpot {
  x: number
  y: number
  below?: boolean
  size?: number
  anchor?: 'left' | 'right'
}

export interface StoryState {
  id: string
  layout: {
    label: LayoutSpot
    heading: LayoutSpot
    note: LayoutSpot
  }
  eyebrow: string
  heading: string[]
  body: string
  range: [number, number]
  fadeIn: [number, number]
  fadeOut: [number, number]
  showMachineState?: boolean
  showConnections?: boolean
  showJourney?: boolean
  cta?: { label: string; href: string }
}

export const storyStates: StoryState[] = [
  {
    id: 'machine',
    layout: {
      label: { x: 75.5, y: 28 },
      heading: { x: 75.5, y: 32, size: 3.1, anchor: 'left' },
      note: { x: 75.5, y: 51, anchor: 'left' },
    },
    eyebrow: '01 — THE MACHINE',
    heading: ['A MACHINE', 'IS SOLD.'],
    body: 'THE JOURNEY BEGINS.',
    range: [0.0, 0.16],
    fadeIn: [-0.02, 0.012],
    fadeOut: [0.11, 0.16],
  },
  {
    id: 'installed-base',
    layout: {
      label: { x: 75.5, y: 6, below: true },
      heading: { x: 75.5, y: 9, below: true, size: 3.1, anchor: 'left' },
      note: { x: 6, y: 86, anchor: 'left' },
    },
    eyebrow: '02 — INSTALLED BASE',
    heading: ['THE SALE', "ISN'T THE", 'END.'],
    body: 'A LIFETIME BEGINS AT HANDOVER.',
    range: [0.16, 0.32],
    fadeIn: [0.155, 0.205],
    fadeOut: [0.28, 0.33],
    showMachineState: true,
  },
  {
    id: 'ecosystem',
    layout: {
      label: { x: 76, y: 2, below: true },
      heading: { x: 76, y: 5, below: true, size: 2.3, anchor: 'left' },
      note: { x: 6, y: 86, anchor: 'left' },
    },
    eyebrow: '03 — AFTER-SALES',
    heading: ['THE MACHINE', 'BECOMES', 'AN ECOSYSTEM.'],
    body: 'EVERY COMPONENT CARRIES A RELATIONSHIP.',
    range: [0.32, 0.56],
    fadeIn: [0.315, 0.365],
    fadeOut: [0.42, 0.48],
    showConnections: true,
  },
  {
    id: 'parts-services',
    layout: {
      label: { x: 5.6, y: 1.5, below: true },
      heading: { x: 5.6, y: 4, below: true, size: 2.4, anchor: 'left' },
      note: { x: 96, y: 2, below: true, anchor: 'right' },
    },
    eyebrow: '04 — PARTS & SERVICES',
    heading: ['PARTS & SERVICES'],
    body: 'PARTS. SERVICE. DATA. NETWORK.',
    range: [0.56, 0.7],
    fadeIn: [0.555, 0.605],
    fadeOut: [0.66, 0.71],
    showConnections: true,
  },
  {
    id: 'journey',
    layout: {
      label: { x: 5.6, y: 1.5, below: true },
      heading: { x: 5.6, y: 4, below: true, size: 2.2, anchor: 'left' },
      note: { x: 96, y: 2, below: true, anchor: 'right' },
    },
    eyebrow: '05 — FROM ISSUE TO UPTIME',
    heading: ['FROM ISSUE TO UPTIME.'],
    body: 'ONE ROUTE. NINE STAGES.',
    range: [0.7, 0.84],
    fadeIn: [0.695, 0.745],
    fadeOut: [0.82, 0.87],
    showJourney: true,
  },
  {
    id: 'uptime',
    layout: {
      label: { x: 75.5, y: 27 },
      heading: { x: 75.5, y: 30.5, size: 2.7, anchor: 'left' },
      note: { x: 75.5, y: 45, anchor: 'left' },
    },
    eyebrow: '06 — UPTIME',
    heading: ['THE MACHINE', 'WORKS.'],
    body: 'THE JOURNEY CONTINUES.',
    range: [0.84, 1.0],
    fadeIn: [0.86, 0.91],
    fadeOut: [1.01, 1.02], // never fades out
    cta: { label: 'ENTER THE AFTER-SALES ECOSYSTEM', href: '#after-sales' },
  },
]

/**
 * Scroll progress → position in the clip (0..1 of its length).
 *
 * Deliberately non-linear. The clip runs whole machine → fully separated, so
 * the last state plays it *backwards*: the machine is taken apart to reveal
 * the after-sales ecosystem, then brought back together by uptime. The hold
 * in the middle keeps it fully exploded while the ecosystem and the journey
 * are read.
 */
const VIDEO_CURVE: [number, number][] = [
  // Scroll position -> position in the clip. MONOTONIC, deliberately.
  //
  // This curve used to end [0.84, 1.0], [1.0, 0.0]: the last stretch of
  // downward scroll ran the frame index backwards through the whole
  // sequence. That is what produced a reversal on the way down and a second
  // disassembly on the way up. It made sense when the clip was a rotation
  // that had to be rewound to look reassembled; it is wrong now, because the
  // sequence contains its own reassembly (frames 61-76) and its own finished
  // machine (77-90). Playing forward is the story.
  //
  // The six states the Hero is read in land as:
  //   01 complete        p 0.00  -> clip 0.00  (frame 1)
  //   02 opening         p 0.20  -> clip 0.19  (frame ~18, separation begins)
  //   03 more open       p 0.38  -> clip 0.40  (frame ~36)
  //   04 fully open      p 0.58  -> clip 0.62  (frame ~56, peak dispersion)
  //   05 closing         p 0.78  -> clip 0.80  (frame ~72, reassembly)
  //   06 complete again  p 0.90+ -> clip 1.00  (frame 90, held to the end)
  [0.0, 0.0],
  [0.2, 0.19],
  [0.38, 0.4],
  [0.58, 0.62],
  [0.78, 0.8],
  [0.9, 1.0],
  // A settling hold on the finished machine, so the end reads as arrival
  // rather than as the animation simply running out.
  [1.0, 1.0],
]

export function progressToClipPosition(progress: number): number {
  const p = clamp(progress, 0, 1)
  for (let i = 1; i < VIDEO_CURVE.length; i += 1) {
    const prev = VIDEO_CURVE[i - 1]
    const curr = VIDEO_CURVE[i]
    if (!prev || !curr) continue
    const [p0, v0] = prev
    const [p1, v1] = curr
    if (p <= p1) {
      const t = p1 === p0 ? 0 : (p - p0) / (p1 - p0)
      return v0 + (v1 - v0) * t
    }
  }
  const last = VIDEO_CURVE[VIDEO_CURVE.length - 1]
  return last ? last[1] : 0
}

/**
 * The camera no longer moves, and that is a deliberate trade.
 *
 * It used to ease back while the machine was apart, to open negative space for
 * the callout labels. But the picture is full-bleed now — that is what removes
 * the frame edge, by leaving no margin for the studio to meet the page at —
 * and scaling it down re-opens exactly those margins, putting the rectangle
 * back at precisely the states where the machine is widest.
 *
 * Overscanning to compensate does not work either: the picture may be cropped
 * vertically but not horizontally, and enough overscan to cover the pull-back
 * would trim the top of the boom, which reaches y 0.025 while separating.
 *
 * The function stays because the connection layer takes a scale when mapping
 * component anchors into stage pixels, and one day the camera may move again.
 *
 * Both the sequence and the connection layer read this, so anchors stay on
 * their components.
 */
export function stageScale(): number {
  // The frames are composed tighter than the page wants: at 1:1 the boom
  // reached the top edge and the exploded components ran to the sides. This
  // is a uniform 12% reduction of the whole stage — the source frames are
  // never cropped, so proportions are untouched and every component stays
  // inside the viewport with room around it.
  return 0.88
}

/** Linear ramp with smoothstep easing: 0 before `from`, 1 after `to`. */
export function ramp(progress: number, from: number, to: number): number {
  if (to <= from) return progress >= to ? 1 : 0
  const t = (progress - from) / (to - from)
  return t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t)
}

/** Opacity of a story state at a given progress value. */
export function stateOpacity(state: StoryState, progress: number): number {
  return Math.min(
    ramp(progress, state.fadeIn[0], state.fadeIn[1]),
    1 - ramp(progress, state.fadeOut[0], state.fadeOut[1]),
  )
}

/** Index of the state that currently dominates — drives the story rail. */
export function activeStateIndex(progress: number): number {
  for (let i = storyStates.length - 1; i >= 0; i -= 1) {
    const state = storyStates[i]
    if (state && progress >= state.range[0]) return i
  }
  return 0
}

/** How far through a single state we are, 0..1. */
export function stateProgress(state: StoryState, progress: number): number {
  const [start, end] = state.range
  return clamp((progress - start) / (end - start), 0, 1)
}

export function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value
}
