import type { Edge, GroundNode } from '../types/ground'

/**
 * Places the visible graph as a hierarchy running down the page.
 *
 * WHERE THE HIERARCHY COMES FROM
 * ------------------------------
 * It used to come from a `column` authored on each node, and that number did
 * not describe a hierarchy. The whole sales spine — machine sold, customer,
 * sales, order, delivery, handover, after-sales — sat in column 0, so it was
 * drawn as a single horizontal row and read as a flowchart rather than as the
 * top of a tree. All twenty-seven business processes sat in column 4, which
 * is a row no screen can hold.
 *
 * Rank is now computed from the relationships themselves: a node sits one
 * level below the lowest thing on screen that feeds it. That is a hierarchy
 * by construction, and it comes from the same edges the connectors are drawn
 * from, so the picture cannot disagree with the model.
 *
 * WHY THE VISIBLE SUBGRAPH, NOT THE WHOLE MODEL
 * ---------------------------------------------
 * Ranking all seventy-two nodes at once gives a twenty-eight-level ribbon one
 * node wide: a single cross-link — monitoring raising a parts requirement —
 * drags the entire parts chain below the entire service chain. Ranked over
 * the five to twenty nodes actually on screen that cannot happen, and every
 * view it produces has no crossing connectors and none pointing back up.
 *
 * WIDTH IS MEASURED, NOT FIXED
 * ----------------------------
 * Every node used to be the same 220px rectangle, which is most of why the
 * page read as a stack of cards. A node is now as wide as its own name.
 */

/** Height of an ordinary node. */
const NODE_H = 42
/** The spine and the five domains carry more weight — see `isMajor`. */
const MAJOR_H = 54
/** Space either side of the label inside a node. */
const PAD_X = 17
/** The type dot and the gap after it. */
export const DOT_LANE = 22
/** The expand chip, on nodes that have one. */
const CHIP_W = 36

/** Horizontal space between siblings on a level. */
const COL_GAP = 34
/** Vertical space between one level and the next.
    Depth is what this graph spends its height on, and height is what a laptop
    has least of. At 64 a six-level view — which is what the dealer network is,
    once the links among its own children are honoured — stood 758px tall in a
    629px canvas and the camera had to drop to 0.647 to hold it. That renders
    an 11.5px label at 7.4px: the nodes are drawn, and nobody can read them.
    Every level saved here is a level the reader gets at full size. */
const ROW_GAP = 46

/* There is no ROW_PITCH any more. Every row used to be spaced at
   MAJOR_H + ROW_GAP whether or not it held anything MAJOR_H tall, and most
   rows hold 42px process steps — so most rows carried twelve pixels of
   nothing, and the camera, which on these views is always pinned by height
   rather than width, spent it out of the size of the labels. Rows are now
   measured; see rowHeight in layoutGraph. */

/**
 * How wide a name is, actually measured.
 *
 * Estimating from character count is wrong by enough to matter: "Hub — Every
 * Angle" and "Parts Requirement" are within a character of each other and
 * differ by 14px on screen, so an estimate either runs the label under the
 * chip or leaves a hole in half the nodes. Measured once per label and
 * remembered; there are seventy-two of them.
 */
const widthCache = new Map<string, number>()
let ctx: CanvasRenderingContext2D | null | undefined

function textWidth(text: string, px: number, weight: number): number {
  const key = `${weight}|${px}|${text}`
  const hit = widthCache.get(key)
  if (hit !== undefined) return hit

  if (ctx === undefined) {
    ctx =
      typeof document === 'undefined'
        ? null
        : document.createElement('canvas').getContext('2d')
  }
  let w: number
  if (ctx) {
    ctx.font = `${weight} ${px}px Inter, "Helvetica Neue", Arial, sans-serif`
    w = ctx.measureText(text).width
  } else {
    // No DOM. Close enough to lay out without throwing.
    w = text.length * px * 0.56
  }
  widthCache.set(key, w)
  return w
}

/** The spine and the five after-sales domains are the structure. */
function isMajor(node: GroundNode): boolean {
  return node.type === 'milestone' || node.type === 'stage' || node.type === 'pillar'
}

function nodeSize(node: GroundNode, hasChip: boolean) {
  const major = isMajor(node)
  const h = major ? MAJOR_H : NODE_H
  const label = textWidth(node.label, major ? 13.5 : 11.5, major ? 700 : 600)
  const w = Math.max(
    major ? 156 : 118,
    Math.ceil(DOT_LANE + label + PAD_X + (hasChip ? CHIP_W : 0)),
  )
  return { w, h, major }
}

interface PlacedNode {
  node: GroundNode
  x: number
  y: number
  w: number
  h: number
  cx: number
  cy: number
  major: boolean
  /** Where the layout put this node's top, before any dragging. */
  row: number
  rank: number
}

interface PlacedEdge {
  edge: Edge
  path: string
  midX: number
  midY: number
}

export interface Layout {
  nodes: PlacedNode[]
  edges: PlacedEdge[]
  byId: Map<string, PlacedNode>
  levels: { rank: number; y: number; count: number }[]
  width: number
  height: number
}

/** A displacement the reader has applied to one node by dragging it. */
export interface NodeOffset {
  dx: number
  dy: number
}

/**
 * Levels, from the relationships on screen.
 *
 * A node sits one below the lowest thing that feeds it. A node nothing on
 * screen feeds — a monitoring feed arriving from a branch that is not open —
 * is lifted to just above whatever it does feed, rather than being stranded
 * at the top of the picture beside the start of the story.
 */
function rankNodes(shown: GroundNode[], allEdges: readonly Edge[]): Map<string, number> {
  const ids = new Set(shown.map((n) => n.id))
  const live = allEdges.filter((e) => e.from !== e.to && ids.has(e.from) && ids.has(e.to))

  const after = new Map<string, string[]>()
  const before = new Map<string, string[]>()
  const waiting = new Map<string, number>()
  shown.forEach((n) => {
    after.set(n.id, [])
    before.set(n.id, [])
    waiting.set(n.id, 0)
  })
  live.forEach((e) => {
    ;(after.get(e.from) as string[]).push(e.to)
    ;(before.get(e.to) as string[]).push(e.from)
    waiting.set(e.to, (waiting.get(e.to) as number) + 1)
  })

  const rank = new Map<string, number>(shown.map((n) => [n.id, 0]))
  const queue = shown.filter((n) => waiting.get(n.id) === 0).map((n) => n.id)
  let settled = 0
  while (queue.length) {
    const at = queue.shift() as string
    settled++
    ;(after.get(at) as string[]).forEach((to) => {
      rank.set(to, Math.max(rank.get(to) as number, (rank.get(at) as number) + 1))
      const left = (waiting.get(to) as number) - 1
      waiting.set(to, left)
      if (left === 0) queue.push(to)
    })
  }

  // A loop inside the view. The model has none today, but it is a mesh and
  // one could be authored, so fall back to something stable.
  if (settled < shown.length) {
    shown.forEach((n, i) => {
      if ((waiting.get(n.id) as number) > 0) rank.set(n.id, i)
    })
  }

  // Lift the stranded. Repeated, because one orphan can feed another.
  for (let pass = 0; pass < 4; pass++) {
    let moved = false
    shown.forEach((n) => {
      const parents = before.get(n.id) as string[]
      const children = after.get(n.id) as string[]
      if (parents.length > 0 || children.length === 0) return
      const lowest = Math.min(...children.map((c) => rank.get(c) as number))
      if (rank.get(n.id) !== lowest - 1) {
        rank.set(n.id, lowest - 1)
        moved = true
      }
    })
    if (!moved) break
  }

  const min = Math.min(...[...rank.values()])
  if (min !== 0) rank.forEach((v, k) => rank.set(k, v - min))
  return rank
}

/**
 * Orders each level so the connectors between levels do not cross.
 *
 * A barycentre sweep: a node wants to sit above the average position of the
 * things it connects to on neighbouring levels, and running that up and down
 * settles the whole picture. What this replaces could only sort a sequence
 * within one row, and did nothing whatever about lines crossing between rows.
 */
function orderLevels(
  levels: Map<number, GroundNode[]>,
  allEdges: readonly Edge[],
  ids: Set<string>,
) {
  const neighbours = new Map<string, string[]>()
  const link = (a: string, b: string) => {
    const list = neighbours.get(a)
    if (list) list.push(b)
    else neighbours.set(a, [b])
  }
  allEdges.forEach((e) => {
    if (e.from === e.to || !ids.has(e.from) || !ids.has(e.to)) return
    link(e.from, e.to)
    link(e.to, e.from)
  })

  const rankOf = new Map<string, number>()
  levels.forEach((list, r) => list.forEach((n) => rankOf.set(n.id, r)))
  const pos = new Map<string, number>()
  levels.forEach((list) => list.forEach((n, i) => pos.set(n.id, i)))

  const ranks = [...levels.keys()].sort((a, b) => a - b)
  for (let sweep = 0; sweep < 8; sweep++) {
    const order = sweep % 2 === 0 ? ranks : [...ranks].reverse()
    order.forEach((r) => {
      const row = levels.get(r) as GroundNode[]
      if (row.length < 2) return
      const key = new Map<string, number>()
      row.forEach((n) => {
        const near = (neighbours.get(n.id) ?? []).filter(
          (o) => pos.has(o) && rankOf.get(o) !== r,
        )
        key.set(
          n.id,
          near.length
            ? near.reduce((sum, o) => sum + (pos.get(o) as number), 0) / near.length
            : (pos.get(n.id) as number),
        )
      })
      row.sort((a, b) => (key.get(a.id) as number) - (key.get(b.id) as number))
      row.forEach((n, i) => pos.set(n.id, i))
    })
  }
}

export function layoutGraph(
  allNodes: readonly GroundNode[],
  allEdges: readonly Edge[],
  visible: ReadonlySet<string>,
  expandable?: (id: string) => boolean,
  offsets?: ReadonlyMap<string, NodeOffset>,
): Layout {
  const shown = allNodes.filter((n) => visible.has(n.id))
  if (shown.length === 0) {
    return { nodes: [], edges: [], byId: new Map(), levels: [], width: 1, height: 1 }
  }

  const ids = new Set(shown.map((n) => n.id))
  const rank = rankNodes(shown, allEdges)

  const levels = new Map<number, GroundNode[]>()
  shown.forEach((n) => {
    const r = rank.get(n.id) as number
    const list = levels.get(r)
    if (list) list.push(n)
    else levels.set(r, [n])
  })
  orderLevels(levels, allEdges, ids)

  const size = new Map<string, { w: number; h: number; major: boolean }>()
  shown.forEach((n) => size.set(n.id, nodeSize(n, Boolean(expandable?.(n.id)))))

  const rows = [...levels.keys()].sort((a, b) => a - b)
  const rowWidth = new Map<number, number>()
  rows.forEach((r) => {
    const list = levels.get(r) as GroundNode[]
    rowWidth.set(
      r,
      list.reduce((sum, n) => sum + (size.get(n.id) as { w: number }).w, 0) +
        COL_GAP * (list.length - 1),
    )
  })
  const width = Math.max(...rowWidth.values())

  const placed: PlacedNode[] = []
  const byId = new Map<string, PlacedNode>()
  const levelInfo: Layout['levels'] = []

  /**
   * How tall each row actually is, rather than assuming every row holds the
   * tallest kind of node there is.
   *
   * Every row used to be pitched at MAJOR_H + ROW_GAP — 100px — whether it
   * held a 54px milestone or a 42px process step. Most rows hold process
   * steps, so most rows were carrying twelve pixels of nothing, and a
   * seven-rank drill paid eighty-four pixels for it. Height is what the
   * camera runs out of first on these views: the graph is a chain one or two
   * boxes wide, so the scale is always pinned by height, never by width, and
   * every pixel of unused height came straight off the size of the labels.
   */
  const rowTop: number[] = []
  const rowHeight: number[] = []
  let cursor = 0
  rows.forEach((r, slot) => {
    const list = levels.get(r) as GroundNode[]
    const tallest = Math.max(
      ...list.map((n) => (size.get(n.id) as { h: number }).h),
    )
    rowTop[slot] = cursor
    rowHeight[slot] = tallest
    cursor += tallest + ROW_GAP
  })

  rows.forEach((r, slot) => {
    const list = levels.get(r) as GroundNode[]
    const y = rowTop[slot] as number
    const band = rowHeight[slot] as number
    let x = (width - (rowWidth.get(r) as number)) / 2
    levelInfo.push({ rank: r, y, count: list.length })

    list.forEach((node) => {
      const s = size.get(node.id) as { w: number; h: number; major: boolean }
      const off = offsets?.get(node.id)
      // Centred within the row's own height, so a 42px node and a 54px one
      // sitting on the same level share a centre line rather than a top.
      const top = y + (band - s.h) / 2
      const px = x + (off ? off.dx : 0)
      const py = top + (off ? off.dy : 0)
      const p: PlacedNode = {
        node,
        x: px,
        y: py,
        w: s.w,
        h: s.h,
        cx: px + s.w / 2,
        cy: py + s.h / 2,
        major: s.major,
        row: top,
        rank: r,
      }
      placed.push(p)
      byId.set(node.id, p)
      x += s.w + COL_GAP
    })
  })

  const edges: PlacedEdge[] = []
  allEdges.forEach((edge) => {
    const a = byId.get(edge.from)
    const b = byId.get(edge.to)
    if (!a || !b) return

    // Same level: a link along a row, leaving and arriving at facing sides.
    if (a.rank === b.rank) {
      const right = b.cx > a.cx
      const xA = right ? a.x + a.w : a.x
      const xB = right ? b.x : b.x + b.w

      /* Neighbours in the row link edge to edge, which reads as the sequence
         it is. Two nodes further apart cannot: drawn across the row the line
         runs straight through every node between them — through their names —
         and claims relationships that are not in the model. The dealer row is
         where this shows: the network's five children sit side by side, and
         the links among them skip two and three at a time. */
      const between = placed.filter(
        (p) =>
          p.rank === a.rank &&
          p !== a &&
          p !== b &&
          p.x + p.w > Math.min(xA, xB) &&
          p.x < Math.max(xA, xB),
      )
      if (between.length) {
        const dip = Math.max(a.y + a.h, b.y + b.h, ...between.map((p) => p.y + p.h)) + 26
        return void edges.push({
          edge,
          path:
            `M ${a.cx} ${a.y + a.h} C ${a.cx} ${dip}, ${b.cx} ${dip}, ${b.cx} ${b.y + b.h}`,
          midX: (a.cx + b.cx) / 2,
          midY: dip + 12,
        })
      }

      const reach = (xB - xA) * 0.4
      edges.push({
        edge,
        path: `M ${xA} ${a.cy} C ${xA + reach} ${a.cy}, ${xB - reach} ${b.cy}, ${xB} ${b.cy}`,
        midX: (xA + xB) / 2,
        midY: Math.max(a.y + a.h, b.y + b.h) + 15,
      })
      return
    }

    // Down the page: leave the bottom, arrive at the top. Ranking makes every
    // connector point downward, so this is the only case that matters and the
    // arrowhead confirms the direction rather than being the only clue to it.
    const down = b.rank > a.rank
    const from = down ? a : b
    const to = down ? b : a
    const x1 = from.cx
    const y1 = from.y + from.h
    const x2 = to.cx
    const y2 = to.y
    const bend = Math.max(22, (y2 - y1) * 0.44)

    /* An edge that skips a level has to go around what it skips.
       The story's own spine does this: a machine is sold to a customer AND
       the sale leads to handover, so machine-sold reaches sales both through
       the customer and directly. Both are centred, so the direct connector
       ran straight down through the middle of the Customer node — through its
       name — which is the one thing a connector must never do. */
    const skipped = Math.abs(to.rank - from.rank) > 1
    if (skipped) {
      const lo = Math.min(from.rank, to.rank)
      const hi = Math.max(from.rank, to.rank)
      const corridorL = Math.min(x1, x2) - 10
      const corridorR = Math.max(x1, x2) + 10
      const inTheWay = placed.filter(
        (p) => p.rank > lo && p.rank < hi && p.x < corridorR && p.x + p.w > corridorL,
      )
      if (inTheWay.length) {
        /* One level skipped, and one thing in the way — the opening view's
           own "machine sold leads to the sale as well as to the customer" —
           needs no staircase at all. Squared off it drew a bracket around
           the Customer node, which on the first screen a client sees reads
           as a box grouping something rather than as a line going past it.
           A single bow clears one row in one movement; verified the same
           way everything else here is — it must not pass through anything. */
        if (hi - lo === 2) {
          const spanned = placed.filter((p) => p.rank > lo && p.rank < hi)
          const CLEAR = 18
          const lanes: number[] = [
            Math.min(...spanned.map((p) => p.x)) - CLEAR,
            Math.max(...spanned.map((p) => p.x + p.w)) + CLEAR,
          ]
          const byLeft = [...spanned].sort((p, q) => p.x - q.x)
          byLeft.forEach((p, i) => {
            const next = byLeft[i + 1]
            if (!next) return
            const gap = next.x - (p.x + p.w)
            if (gap >= CLEAR * 2) lanes.push(p.x + p.w + gap / 2)
          })
          const mid = (x1 + x2) / 2
          const via = lanes
            .filter((lane) => spanned.every((p) => lane < p.x - 2 || lane > p.x + p.w + 2))
            .sort((p, q) => Math.abs(p - mid) - Math.abs(q - mid))[0] as number
          const swing = via + (via > x1 ? 12 : -12)
          edges.push({
            edge,
            path:
              `M ${x1} ${y1} C ${x1} ${y1 + bend * 0.7}, ${swing} ${y1 + 8}, ` +
              `${swing} ${(y1 + y2) / 2} S ${x2} ${y2 - bend * 0.7}, ${x2} ${y2}`,
            midX: swing,
            midY: (y1 + y2) / 2,
          })
          return
        }

        /* Two or more rows skipped: a staircase, not one long jump.
           This used to pick ONE lane clear of every row being skipped at
           once and route the whole distance out to it — correct, nothing
           was ever crossed, but a link that only had to dodge one crowded
           row could end up swung a third of the way across the canvas and
           back, because some OTHER row further down also had to fit under
           that same single lane. The network's link to the service engineer
           did exactly this: forced out around Regional Support two rows
           down, when the row immediately below it had room right there.

           Each row is now judged on its own. A column that already clears a
           row is kept; only a row that actually blocks it gets a sidestep,
           taken in the gap directly above that row — where nothing is drawn
           — and the path drops back toward the direct line the moment the
           next row lets it. The result hugs the straight line between the
           two nodes and only leaves it where something is actually there. */
        const CLEAR = 18
        const R = 16
        const bandY = (r: number) => (levelInfo.find((l) => l.rank === r) as { y: number }).y
        const rowNodes = (r: number) => placed.filter((p) => p.rank === r)

        const midRanks = levelInfo
          .map((l) => l.rank)
          .filter((r) => r > lo && r < hi)
          .sort((p, q) => p - q)

        const laneFor = (r: number, interp: number): number => {
          const here = rowNodes(r)
          const blocked = here.some((p) => interp > p.x - 3 && interp < p.x + p.w + 3)
          if (!blocked) return interp
          const sorted = [...here].sort((p, q) => p.x - q.x)
          const first = sorted[0] as PlacedNode
          const last = sorted[sorted.length - 1] as PlacedNode
          const candidates: number[] = [first.x - CLEAR, last.x + last.w + CLEAR]
          sorted.forEach((p, i) => {
            const next = sorted[i + 1]
            if (!next) return
            const gap = next.x - (p.x + p.w)
            if (gap >= CLEAR * 2) candidates.push(p.x + p.w + gap / 2)
          })
          // The two outer candidates are clear of `here` by construction, so
          // this list is never empty and the sort always has a first element.
          return candidates
            .filter((lane) => here.every((p) => lane < p.x - 3 || lane > p.x + p.w + 3))
            .sort((p, q) => Math.abs(p - interp) - Math.abs(q - interp))[0] as number
        }

        const steps = midRanks.length + 1 // number of hops from `from` to `to`
        const colOf = new Map<number, number>(midRanks.map((r, i) => {
          const interp = x1 + ((x2 - x1) * (i + 1)) / steps
          return [r, laneFor(r, interp)]
        }))

        let d = `M ${x1} ${y1}`
        let curX = x1
        let curY = y1
        const stops = [...midRanks, hi]
        stops.forEach((r, i) => {
          const arriving = colOf.get(r) ?? x2 // hi itself is never in colOf
          const isLast = i === stops.length - 1
          const rowTop = isLast ? y2 : bandY(r)
          const gapMid = (curY + rowTop) / 2
          if (Math.abs(arriving - curX) < 1) {
            d += ` V ${rowTop}`
          } else {
            const s = arriving > curX ? 1 : -1
            d +=
              ` V ${gapMid - R} Q ${curX} ${gapMid} ${curX + s * R} ${gapMid}` +
              ` H ${arriving - s * R} Q ${arriving} ${gapMid} ${arriving} ${gapMid + R}` +
              ` V ${rowTop}`
          }
          curX = arriving
          curY = rowTop
          if (!isLast) {
            /* Through this row's own band before judging the next gap.
               Measured from the row, not from MAJOR_H: rows are now only as
               tall as what they hold, so a fixed 54 would drop the path
               below a 42px row and start the next sidestep inside the gap
               it was supposed to begin after. */
            const slotOf = rows.indexOf(r)
            curY = bandY(r) + ((rowHeight[slotOf] as number | undefined) ?? MAJOR_H)
            d += ` V ${curY}`
          }
        })

        edges.push({ edge, path: d, midX: (x1 + x2) / 2, midY: (y1 + y2) / 2 })
        return
      }
    }

    edges.push({
      edge,
      path: `M ${x1} ${y1} C ${x1} ${y1 + bend}, ${x2} ${y2 - bend}, ${x2} ${y2}`,
      midX: (x1 + x2) / 2,
      midY: (y1 + y2) / 2,
    })
  })

  /* The bottom of the last row, measured rather than assumed: with per-row
     heights the last row is not necessarily MAJOR_H tall, and overstating it
     hands the camera a graph taller than the one it is fitting. */
  const lastY = levelInfo.length ? (levelInfo[levelInfo.length - 1] as { y: number }).y : 0
  const lastH = rowHeight.length ? (rowHeight[rowHeight.length - 1] as number) : MAJOR_H
  return { nodes: placed, edges, byId, levels: levelInfo, width, height: lastY + lastH }
}
