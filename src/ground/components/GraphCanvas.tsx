import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { Edge, GroundNode } from '../types/ground'
import type { GraphState } from '../hooks/useGraphState'
import { CONFIDENCE_LABELS, NODE_TYPE_LABELS } from '../data/graph'
import type { NodeOffset } from '../utils/layout'
import { DOT_LANE, layoutGraph } from '../utils/layout'

/**
 * The graph itself — the main experience, not an illustration beside one.
 *
 * Left to right, one column per architectural layer, curved connectors
 * carrying their flow labels. The canvas is deliberately larger than the
 * viewport: it can be panned and zoomed, and it re-fits itself whenever the
 * visible graph changes, so opening a layer brings the new material into
 * view instead of leaving it off-screen.
 *
 * SVG rather than DOM nodes because the connectors are the substance here —
 * they have to curve, carry labels, and light up as a traced path.
 */

/* Margin the automatic fit leaves around the graph. Generous padding is
   cheap on a tall window and expensive on a short one, where it was taking
   136px out of a 629px canvas — more than a whole level of the hierarchy. */
const PAD = 40
/** Spacing of the canvas grid, in graph units. */
const GRID = 28

/** Node labels are set at this size in the stylesheet. */
const LABEL_PX = 11.5
/** Below roughly this on screen a label is no longer worth drawing.
    Node labels are set at 11.5px rather than the 10.5px this floor was first
    chosen against, so the same fraction now buys a physically larger label —
    which is what lets the deepest views hold their route context on screen
    instead of pushing the top of it past the edge of the frame. */
const MIN_LABEL_PX = 7
/**
 * The floor the automatic camera will not go below. Fitting the whole graph
 * used to win every argument, which meant that past a certain size the page
 * answered "here is everything, none of it readable" — at full expansion the
 * labels came out at 2.9px. Legibility wins instead, and what will not fit is
 * reached by panning.
 */
const MIN_AUTO_K = MIN_LABEL_PX / LABEL_PX
/* How large the automatic camera will draw the graph.
   This was 1.05 — effectively "never bigger than authored" — which suited a
   canvas holding the whole model. Holding one path, the graph is a narrow
   ribbon in a wide frame, and refusing to scale it up left a five-box flow
   floating in the middle of a 1440px screen at reading size. It is allowed to
   grow into the room it has; the ceiling is only there so a two-box view does
   not become a poster. */
const MAX_K = 1.34
/** Only reachable deliberately, through Fit or the zoom control. */
const ABS_MIN_K = 0.22

interface FitOptions {
  /** Where to centre when the graph cannot be shown legibly all at once. */
  focus?: { cx: number; cy: number }
  /** Fit really does mean fit: let it go under the legibility floor. */
  allowSmall?: boolean
}

function computeFit(
  size: { w: number; h: number },
  graph: { width: number; height: number },
  { focus, allowSmall }: FitOptions = {},
) {
  const availW = Math.max(160, size.w - PAD * 2)
  const availH = Math.max(160, size.h - PAD * 2)
  const whole = Math.min(
    MAX_K,
    availW / Math.max(1, graph.width),
    availH / Math.max(1, graph.height),
  )

  // It fits legibly, or the reader has asked for the overview regardless.
  if (allowSmall || whole >= MIN_AUTO_K) {
    const k = Math.max(allowSmall ? ABS_MIN_K : MIN_AUTO_K, whole)
    return {
      k,
      x: PAD + (availW - graph.width * k) / 2,
      y: PAD + (availH - graph.height * k) / 2,
    }
  }

  // It does not. Hold a readable scale and put the node just opened in the
  // middle, so expanding a branch moves the camera to that branch instead of
  // shrinking the whole map away from the reader.
  const cx = focus ? focus.cx : graph.width / 2
  const cy = focus ? focus.cy : graph.height / 2
  return {
    k: MIN_AUTO_K,
    x: size.w / 2 - cx * MIN_AUTO_K,
    y: size.h / 2 - cy * MIN_AUTO_K,
  }
}

interface Props {
  nodes: readonly GroundNode[]
  edges: readonly Edge[]
  state: GraphState
}

/* No `reducedMotion` prop any more. Nothing here animates: the camera is
   assigned outright, and the one remaining animation — a newly revealed node
   fading in — is turned off in the stylesheet's own reduced-motion block,
   where it belongs. */
export function GraphCanvas({ nodes, edges, state }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<SVGGElement>(null)
  const [size, setSize] = useState({ w: 1200, h: 700 })
  // Pan/zoom the user has applied on top of the automatic fit.
  const [view, setView] = useState({ x: 0, y: 0, k: 1 })
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null)
  const fitted = useRef('')
  /* Where the reader has dragged individual boxes to. The automatic layout is
     still what places everything; this is an adjustment on top of it, kept per
     node id so a branch closed and reopened comes back where it was left. */
  const [offsets, setOffsets] = useState<ReadonlyMap<string, NodeOffset>>(
    () => new Map(),
  )
  const nodeDrag = useRef<{
    id: string
    px: number
    py: number
    dx: number
    dy: number
    moved: boolean
  } | null>(null)
  /* A drag ends with a pointerup over the node, which the browser then reports
     as a click. Without this, letting go of a box you have just moved would
     also re-root the graph on it. */
  const suppressClick = useRef(false)
  /* Read inside pointer handlers, where the render's `view` would be stale. */
  const viewVal = useRef(view)
  viewVal.current = view
  /* Hovering previews a relationship without committing to it. Clicking
     re-roots the whole graph, which is a big move to make just to find out
     what something connects to. */
  const [hoverId, setHoverId] = useState<string | null>(null)
  /* SMIL cannot be turned off from the stylesheet the way a CSS animation
     can, so the travelling marks have to be asked about here rather than
     styled away. */
  const [reducedMotion, setReducedMotion] = useState(false)
  /* Shut by default. The map is meant to be readable without a key; this is
     for the reader who wants to know why one line is dotted and another is
     not, which is a question they only ask once. */
  const [legendOpen, setLegendOpen] = useState(false)
  /* Marks the canvas while a node is under the hand. Nothing depends on it
     for correctness — it is there so the stylesheet can tell a drag from a
     re-layout. */
  const [draggingNode, setDraggingNode] = useState(false)

  /* `isExpandable` is passed in because a node's width depends on whether it
     carries an expand chip, and only the state knows that. */
  const layout = useMemo(
    () => layoutGraph(nodes, edges, state.visible, state.isExpandable, offsets),
    [nodes, edges, state.visible, state.isExpandable, offsets],
  )

  /* The band headings that used to be set down the left — "From Machine to
     After-Sales", "After-Sales Domains", "Outcome" and the rest — are gone,
     along with the hairlines under them. Each box already names what kind of
     thing it is on its second line, so the headings repeated that in a second
     vocabulary, and with the boxes now draggable the rules were labelling
     rows that the reader is free to move things out of. */

  /**
   * How big the canvas actually is.
   *
   * This waited on a ResizeObserver for its first value, and when that
   * observer did not fire the component kept the 1200x700 placeholder it was
   * initialised with. On a 375px phone every fit was then computed against a
   * canvas more than three times too wide: the arithmetic said the graph fit
   * comfortably, so the camera never switched to centring on the selection,
   * and the node the reader had just opened sat off the side of the screen.
   *
   * So the element is measured outright, first, and the observer only keeps
   * that up to date. A resize listener backs it up, because nothing here
   * should depend on any single mechanism firing.
   */
  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return undefined

    const measure = () => {
      const { width, height } = el.getBoundingClientRect()
      if (!width || !height) return
      const w = Math.max(320, width)
      const h = Math.max(280, height)
      setSize((prev) => {
        if (Math.abs(prev.w - w) < 0.5 && Math.abs(prev.h - h) < 0.5) return prev
        // Force the next render to re-fit: keying the fit on the measured size
        // is not enough on its own, because the measurement and the render
        // that reads it can land in an order where the key never differs.
        fitted.current = ''
        return { w, h }
      })
    }

    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    window.addEventListener('resize', measure)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [])

  /**
   * Measures the canvas on every render, and only every render.
   *
   * The ResizeObserver above is a notification, and notifications here have a
   * record of not arriving. The bar changes height whenever the caption
   * appears or wraps, which changes the canvas height under the graph; when
   * the observer did not fire, the camera went on fitting against the height
   * it last knew. That is how selecting Service Engineer came to be drawn at
   * a scale meant for a canvas 130px taller than the real one, with Repair
   * laid out below the bottom of the frame.
   *
   * A bounding rect is cheap and this is the value everything else depends
   * on, so it is read rather than waited for.
   */
  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const { width, height } = el.getBoundingClientRect()
    if (!width || !height) return
    const w = Math.max(320, width)
    const h = Math.max(280, height)
    if (Math.abs(size.w - w) > 0.5 || Math.abs(size.h - h) > 0.5) {
      fitted.current = ''
      setSize({ w, h })
    }
  })

  useEffect(() => {
    const q = window.matchMedia('(prefers-reduced-motion: reduce)')
    const read = () => setReducedMotion(q.matches)
    read()
    q.addEventListener('change', read)
    return () => q.removeEventListener('change', read)
  }, [])

  // Re-fit whenever the visible graph OR the canvas size changes — but not on
  // pan/zoom, or the user could never move away from the fitted position.
  //
  // The key has to include the size: the canvas is measured by a
  // ResizeObserver, so the first render fits against a placeholder size and
  // the real size arrives immediately after. Keying on the node set alone
  // meant that second pass was skipped and the graph stayed unfitted.
  const shape = [...state.visible].sort().join(',')
  const fitKey = `${shape}|${state.selectedId ?? ''}|${Math.round(size.w)}x${Math.round(
    size.h,
  )}|${Math.round(layout.width)}x${Math.round(layout.height)}`

  useEffect(() => {
    if (fitted.current === fitKey) return
    fitted.current = fitKey
    // Set outright and let CSS move the camera. A tween here was being
    // killed a frame after it started — the canvas is measured by a
    // ResizeObserver, so this effect legitimately runs twice on mount, and
    // the second run cancelled the first mid-flight and left the view
    // stranded at the start of the movement.
    // Measured here, now, rather than trusted from state.
    //
    // Every notification this has relied on has failed at least once: the
    // ResizeObserver did not fire when the canvas changed size, and the
    // window resize event never came either. The camera is the one thing that
    // must not be wrong, and a bounding rect is cheap, so it is read at the
    // moment it is needed instead of waiting to be told.
    const el = wrapRef.current
    const rect = el?.getBoundingClientRect()
    const live =
      rect && rect.width > 0 && rect.height > 0
        ? { w: Math.max(320, rect.width), h: Math.max(280, rect.height) }
        : size

    // Keep the state in step so the <svg> is sized correctly too.
    if (Math.abs(live.w - size.w) > 0.5 || Math.abs(live.h - size.h) > 0.5) {
      setSize(live)
    }

    const focus = state.selectedId ? layout.byId.get(state.selectedId) : undefined
    setView(computeFit(live, layout, { focus }))
    // `size`/`layout` are read through the key; listing them again would not
    // change when this runs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey])

  /**
   * Moves the camera. Deliberately without animation.
   *
   * Three different mechanisms have now broken this exact transform, all the
   * same way — by holding a value the graph had already moved past. GSAP
   * rewrote the `transform` attribute and collapsed revealed nodes onto the
   * first column. A CSS transition on `transform` did not animate an SVG
   * group at all; it blocked the new value, so the style read as current
   * while the painted matrix stayed on the old one and the view appeared
   * frozen after Expand all. The Web Animations API then pinned the group to
   * the animation's first keyframe, because an animation that cannot tick
   * never finishes and never releases what it is holding.
   *
   * The pattern is that anything driving this value over time can strand it.
   * The camera is how the reader is *told where they are*, so it is assigned
   * outright and arrives immediately. A glide would be nicer; being right is
   * worth more, and every attempt at the glide has cost correctness.
   */
  useLayoutEffect(() => {
    const el = viewRef.current
    if (!el) return
    el.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`
  }, [view.x, view.y, view.k])

  const onPointerDown = useCallback(
    (event: React.PointerEvent) => {
      // Capturing the pointer here would swallow the click that follows, so
      // anything interactive on top of the canvas has to opt out of panning.
      if ((event.target as Element).closest('[data-node], .gr__hud')) return
      drag.current = { x: event.clientX, y: event.clientY, vx: view.x, vy: view.y }
      ;(event.currentTarget as Element).setPointerCapture(event.pointerId)
    },
    [view.x, view.y],
  )

  const onPointerMove = useCallback((event: React.PointerEvent) => {
    const d = drag.current
    if (!d) return
    setView((v) => ({ ...v, x: d.vx + (event.clientX - d.x), y: d.vy + (event.clientY - d.y) }))
  }, [])

  const endDrag = useCallback(() => {
    drag.current = null
  }, [])

  /**
   * Dragging a single box.
   *
   * The pointer is captured on the node's own group, so the movement never
   * reaches the canvas underneath and the graph does not pan at the same time.
   * Screen movement is divided by the zoom, or a box would travel further than
   * the hand at high zoom and lag behind it at low.
   */
  const onNodePointerDown = useCallback(
    (event: React.PointerEvent, id: string) => {
      // Let the toggle keep its click; it is a control, not a handle.
      if ((event.target as Element).closest('.gr__n-toggle')) return
      if (event.button !== 0 && event.pointerType === 'mouse') return
      event.stopPropagation()
      const at = offsets.get(id)
      nodeDrag.current = {
        id,
        px: event.clientX,
        py: event.clientY,
        dx: at ? at.dx : 0,
        dy: at ? at.dy : 0,
        moved: false,
      }
      suppressClick.current = false
      /* NO POINTER CAPTURE HERE. It used to be taken on pointerdown, and it
         broke clicking a node outright.

         Capturing retargets the rest of the gesture — including the `click`
         the browser sends afterwards — at the element that took the capture.
         That is this outer group; the click handler is on the `.gr__n-hit`
         inside it. A retargeted click never passes through the child, so it
         never reached the handler, and clicking a node did nothing at all.

         Capture is taken in the move handler instead, at the moment the
         gesture is known to be a drag. A plain click now involves no capture
         and follows the ordinary path. */
    },
    [offsets],
  )

  const onNodePointerMove = useCallback((event: React.PointerEvent) => {
    const d = nodeDrag.current
    if (!d) return
    const k = viewVal.current.k || 1
    const dx = d.dx + (event.clientX - d.px) / k
    const dy = d.dy + (event.clientY - d.py) / k
    // A few pixels of travel is a shaky click, not a drag.
    if (!d.moved && Math.hypot(event.clientX - d.px, event.clientY - d.py) < 4) return
    if (!d.moved) {
      setDraggingNode(true)
      /* Now it is a drag, so hold on to the pointer: past this point the box
         should keep following the hand even when it outruns it. Retargeting
         the click no longer matters — a drag suppresses the click anyway. */
      try {
        ;(event.currentTarget as Element).setPointerCapture(event.pointerId)
      } catch {
        /* not a live pointer (a synthesised event); the drag still tracks
           while the pointer stays over the node */
      }
    }
    d.moved = true
    suppressClick.current = true
    setOffsets((prev) => {
      const next = new Map(prev)
      next.set(d.id, { dx, dy })
      return next
    })
  }, [])

  const onNodePointerUp = useCallback((event: React.PointerEvent) => {
    if (!nodeDrag.current) return
    nodeDrag.current = null
    setDraggingNode(false)
    const el = event.currentTarget as Element
    try {
      if (el.hasPointerCapture(event.pointerId)) el.releasePointerCapture(event.pointerId)
    } catch {
      /* nothing was captured */
    }
  }, [])

  /** Puts every box back where the layout wants it. */
  const resetPositions = useCallback(() => {
    setOffsets(new Map())
    fitted.current = ''
  }, [])

  const onWheel = useCallback((event: React.WheelEvent) => {
    if (!event.ctrlKey && !event.metaKey && Math.abs(event.deltaY) < 2) return
    event.preventDefault()
    const rect = (event.currentTarget as Element).getBoundingClientRect()
    const px = event.clientX - rect.left
    const py = event.clientY - rect.top
    setView((v) => {
      const k = Math.min(1.8, Math.max(ABS_MIN_K, v.k * (event.deltaY > 0 ? 0.92 : 1.08)))
      const ratio = k / v.k
      return { k, x: px - (px - v.x) * ratio, y: py - (py - v.y) * ratio }
    })
  }, [])

  // Newly revealed material fades in via CSS, not GSAP. A node's position
  // lives in its `transform` attribute, and GSAP animating a node group
  // rewrites that attribute — which collapsed every revealed node back onto
  // the first column. Nothing may tween these groups.

  /* Only the connectors touching the selection are lit now, so everything
     else on screen is a relationship the reader can see but is not on. That
     is worth showing quietly rather than at full strength. */
  const hasSelection = state.selectedId !== null && state.litNodes.size > 0
  /**
   * Where each flow caption is printed.
   *
   * These were staggered by counting: every fourth caption dropped a line.
   * Counting knows nothing about where the captions actually are, so it moved
   * ones that were already clear and left ones that were not — selecting a
   * system fanned nine captions into a band and three of them still landed on
   * each other, one of them worse than before the stagger existed.
   *
   * This resolves the collisions instead. Captions are placed top down, and
   * one that would land on a caption already placed is pushed below it until
   * it is clear. Width is estimated from the text rather than measured: the
   * real width is only knowable after layout, and being a few pixels
   * pessimistic costs nothing while measuring would cost a second pass.
   */
  const labelY = useMemo(() => {
    const CHAR_W = 6.2 // 8.5px uppercase at 0.13em tracking, plus its halo
    const LINE_H = 13
    /* An SVG text sits ON its baseline, so the glyphs occupy roughly
       [y - LINE_H, y] rather than [y - LINE_H / 2, y + LINE_H / 2]. Treating
       the caption as centred on y put its collision box four pixels lower
       than the ink, which is how "shipment" came to rest three pixels inside
       Goods Receipt while the test said it was clear. */
    const ABOVE = LINE_H - 3
    const BELOW = 3
    const STEP = 11
    /* Nodes are obstacles too.
       Resolving captions only against each other left them landing on the
       boxes instead — a caption printed across a node's own name, which is
       the one place a connector's label must never be. Every node on screen
       is now in the same set of things to keep clear of. */
    const blockers: { x1: number; x2: number; y1: number; y2: number }[] =
      layout.nodes.map((p) => ({ x1: p.x, x2: p.x + p.w, y1: p.y, y2: p.y + p.h }))
    const out = new Map<number, number>()
    /* A hub reaches several entities the same way — HCME D365 / IDMS is the
       system of record for the part, the sales order, the purchase order and
       the returns order alike — and printing that four times said it four
       times: four identical captions in one fifty-pixel band, on top of the
       genuinely different ones. The relationship is established once; the
       target node's own name is what tells the reader which entity it is
       this time. Repeats of a caption already shown in this same view are
       skipped, so the band holds only what is actually distinct. */
    const shownText = new Set<string>()

    layout.edges
      .map((pe, i) => ({ pe, i }))
      .filter(({ pe }) => {
        if (!pe.edge.label) return false
        const touchesSelection =
          pe.edge.from === state.selectedId || pe.edge.to === state.selectedId
        const touchesHover =
          hoverId !== null && (pe.edge.from === hoverId || pe.edge.to === hoverId)
        return touchesSelection || touchesHover
      })
      .sort((a, b) => a.pe.midY - b.pe.midY || a.pe.midX - b.pe.midX)
      .forEach(({ pe, i }) => {
        const text = pe.edge.label as string
        if (shownText.has(text)) return
        shownText.add(text)
        const half = (text.length * CHAR_W) / 2
        const x1 = pe.midX - half
        const x2 = pe.midX + half
        /* Downward only, and not far. Lifting a caption puts it back into
           the boxes the layout moved it clear of; pushing it a long way is
           worse still. Given forty steps to work with, the caption on a hub's
           link into HCME Annata ended up a hundred pixels below the line it
           belongs to and directly under the node — where it read as that
           node's subtitle rather than as anything to do with a connector.

           Four lines is as far as a caption can travel and still obviously
           belong to its own line. Past that it is not drawn: an unlabelled
           connector is honest, and hovering it brings the label back. */
        let y = pe.midY
        let placedOk = false
        for (let tries = 0; tries <= 4; tries++) {
          const hit = blockers.some(
            (b) => x1 < b.x2 && b.x1 < x2 && y - ABOVE < b.y2 && b.y1 < y + BELOW,
          )
          if (!hit) {
            placedOk = true
            break
          }
          y += STEP
        }
        if (!placedOk) return
        blockers.push({ x1, x2, y1: y - ABOVE, y2: y + BELOW })
        out.set(i, y)
      })

    return out
  }, [layout.nodes, layout.edges, state.selectedId, hoverId])

  /* Which kinds of thing are actually on screen. The legend used to be an
     argument against itself: a fixed key listing nine node types and six
     confidence states, most of which the reader could not see, is longer than
     the picture it explains. Listing only what is in front of them keeps it
     to three or four lines and makes it worth opening. */
  const legend = useMemo(() => {
    const types = new Set<GroundNode['type']>()
    const flags = new Set<string>()
    layout.nodes.forEach(({ node }) => {
      types.add(node.type)
      if (node.provenance.confidence !== 'confirmed') flags.add(node.provenance.confidence)
    })
    const kinds = new Set<Edge['kind']>()
    layout.edges.forEach(({ edge }) => kinds.add(edge.kind))
    return { types: [...types], flags: [...flags], kinds: [...kinds] }
  }, [layout])

  return (
    <div
      className={`gr__canvas${draggingNode ? ' is-dragging' : ''}`}
      ref={wrapRef}
      /* The ground the graph sits on, pinned to the camera rather than to the
         screen. Panning an empty white field gives no feedback at all — the
         boxes slide and nothing else does, so the reader cannot tell whether
         they moved the view or the view moved them. A grid that travels with
         the content makes both pan and zoom legible, and gives the boxes
         something to sit on. */
      style={{
        backgroundSize: `${GRID * view.k}px ${GRID * view.k}px`,
        backgroundPosition: `${view.x}px ${view.y}px`,
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onWheel={onWheel}
    >
      <svg className="gr__svg" width={size.w} height={size.h} role="group" aria-label="Parts and services architecture graph">
        <defs>
          <marker
            id="gr-arrow"
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 7 4 L 0 7 z" className="gr__arrow" />
          </marker>
          <marker
            id="gr-arrow-lit"
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 7 4 L 0 7 z" className="gr__arrow is-lit" />
          </marker>

          {/* A box needs to sit on the ground rather than be printed on it.
              Kept very soft: at presentation size a heavier shadow turns a
              precise architecture diagram into a slide deck. */}
          <filter id="gr-lift" x="-20%" y="-30%" width="140%" height="180%">
            <feDropShadow dx="0" dy="1" stdDeviation="1.6" floodColor="#1f1f1f" floodOpacity="0.08" />
          </filter>
          <filter id="gr-lift-on" x="-40%" y="-60%" width="180%" height="240%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#f15a24" floodOpacity="0.22" />
          </filter>
        </defs>

        {/* The camera is written by an effect — see moveCamera. Nothing about
            the transform is declared here, deliberately. */}
        <g ref={viewRef} style={{ transformOrigin: '0 0' }}>
          {layout.edges.map((pe, i) => {
            const index = edges.indexOf(pe.edge)
            const lit = state.litEdges.has(index)
            const dim = hasSelection && !lit
            const touchesSelection =
              pe.edge.from === state.selectedId || pe.edge.to === state.selectedId
            const touchesHover =
              hoverId !== null && (pe.edge.from === hoverId || pe.edge.to === hoverId)
            /* A caption is drawn only where one could be placed clear of
               everything else — see labelY. */
            const showLabel =
              Boolean(pe.edge.label) &&
              (touchesSelection || touchesHover) &&
              labelY.has(i)
            // Resolved above, so a caption is only moved when something is
            // actually in its way.
            const captionY = labelY.get(i) ?? pe.midY
            return (
              <g key={`e-${pe.edge.from}-${pe.edge.to}-${i}`}>
                <path
                  className={[
                    'gr__edge',
                    `is-${pe.edge.kind}`,
                    `is-${pe.edge.confidence}`,
                    lit ? 'is-lit' : '',
                    touchesHover ? 'is-hover' : '',
                    dim && !touchesHover ? 'is-dim' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  d={pe.path}
                  markerEnd={lit ? 'url(#gr-arrow-lit)' : 'url(#gr-arrow)'}
                />
                {/* A flow is a thing that moves, and a static curve does not
                    say so. One travelling mark per lit connector turns the
                    highlighted route into a direction the eye follows on its
                    own, which is most of what this page has to do in front of
                    a room. Off entirely under reduced motion. */}
                {lit && !reducedMotion && (
                  <circle className="gr__pulse" r={2.4}>
                    <animateMotion
                      dur="2.6s"
                      begin={`${(i % 5) * 0.42}s`}
                      repeatCount="indefinite"
                      path={pe.path}
                      keyPoints="0;1"
                      keyTimes="0;1"
                      calcMode="linear"
                    />
                  </circle>
                )}
                {/* Flow labels only on lit paths — otherwise the canvas is
                    unreadable at full expansion. */}
                {showLabel && (
                  <text
                    className="gr__edge-label"
                    x={pe.midX}
                    y={captionY}
                    textAnchor="middle"
                  >
                    {pe.edge.label}
                  </text>
                )}
              </g>
            )
          })}

          {layout.nodes.map((p) => {
            const n = p.node
            const selected = state.selectedId === n.id
            const lit = state.litNodes.has(n.id)
            const more = state.revealCount(n.id)
            const expandable = more > 0
            const open = state.isOpen(n.id)
            const kind = NODE_TYPE_LABELS[n.type]

            return (
              <g
                key={n.id}
                data-node
                data-fresh="1"
                className={[
                  'gr__n',
                  `is-${n.type}`,
                  p.major ? 'is-major' : '',
                  state.onPath.has(n.id) ? 'is-path' : 'is-branch',
                  selected ? 'is-selected' : '',
                  lit && !selected ? 'is-lit' : '',
                  expandable ? 'is-expandable' : '',
                  open ? 'is-open' : '',
                  offsets.has(n.id) ? 'is-moved' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                /* Positioned through the style rather than the `transform`
                    attribute, because an attribute cannot be transitioned and
                    expanding moves most of what is already on screen. The
                    camera is still assigned outright — that is the transform
                    three separate animation libraries have stranded — but a
                    node group is written by React on every render and has
                    nothing to strand. */
                style={{ transform: `translate(${p.x}px, ${p.y}px)` }}
                onMouseEnter={() => setHoverId(n.id)}
                onMouseLeave={() => setHoverId((h) => (h === n.id ? null : h))}
                onPointerDown={(ev) => onNodePointerDown(ev, n.id)}
                onPointerMove={onNodePointerMove}
                onPointerUp={onNodePointerUp}
                onPointerCancel={onNodePointerUp}
              >
                <g
                  className="gr__n-hit"
                  role="button"
                  tabIndex={0}
                  aria-label={
                    expandable
                      ? `${n.label}, ${kind}. ${more} more connected.`
                      : `${n.label}, ${kind}.`
                  }
                  aria-expanded={expandable ? false : undefined}
                  onClick={() => {
                    // The pointerup that ended a drag also arrives here.
                    if (suppressClick.current) {
                      suppressClick.current = false
                      return
                    }
                    state.activate(n.id)
                  }}
                  onKeyDown={(ev) => {
                    if (ev.key === 'Enter' || ev.key === ' ') {
                      ev.preventDefault()
                      state.activate(n.id)
                    }
                  }}
                >
                  {/* A pill, and only as wide as its own name. Every node used
                      to be the same 220px rectangle with a rule down one edge,
                      which is most of why the page read as a stack of cards
                      rather than as a graph. */}
                  <rect
                    className="gr__n-box"
                    width={p.w}
                    height={p.h}
                    rx={p.h / 2}
                    filter={selected ? 'url(#gr-lift-on)' : 'url(#gr-lift)'}
                  />
                  {/* What kind of thing this is, as a dot. The word itself is
                      in the caption and in the key; on the node it only has to
                      group things by eye. */}
                  <circle className="gr__n-dot" cx={p.major ? 15 : 13} cy={p.h / 2} r={p.major ? 5 : 4} />
                  <text
                    className="gr__n-label"
                    x={p.major ? DOT_LANE + 2 : DOT_LANE - 2}
                    y={p.h / 2}
                    dominantBaseline="central"
                  >
                    {n.label}
                  </text>
                  {/* Anything the model is not certain of says so on its face. */}
                  {n.provenance.confidence !== 'confirmed' && (
                    <circle
                      className={`gr__n-flag is-${n.provenance.confidence}`}
                      cx={p.w - (expandable ? 44 : 12)}
                      cy={9}
                      r={3}
                    >
                      <title>
                        {CONFIDENCE_LABELS[n.provenance.confidence]}
                        {n.provenance.source ? ` — ${n.provenance.source}` : ''}
                      </title>
                    </circle>
                  )}
                </g>

                {/* The expand chip.
                    "+2" in a grey outline said nothing about what it was for;
                    it read as a badge rather than as a control. A chevron says
                    "there is more below this", the number says how much, and
                    the whole node opens it — the chip is a target, not the
                    only one. */}
                {expandable && (
                  <g
                    className="gr__n-chip"
                    role="button"
                    tabIndex={-1}
                    aria-label={`Expand ${n.label}: ${more} connected`}
                    transform={`translate(${p.w - 34} ${p.h / 2 - 9})`}
                    onClick={(ev) => {
                      ev.stopPropagation()
                      if (suppressClick.current) {
                        suppressClick.current = false
                        return
                      }
                      state.activate(n.id)
                    }}
                  >
                    <rect className="gr__n-chip-bg" width={26} height={18} rx={9} />
                    <text className="gr__n-chip-text" x={9} y={9.5} dominantBaseline="central">
                      {more}
                    </text>
                    <path className="gr__n-chip-mark" d="M 16.5 7.5 L 19.5 10.5 L 22.5 7.5" />
                  </g>
                )}
              </g>
            )
          })}
        </g>
      </svg>

      {/* The node count is gone.
          It was the most prominent thing on the canvas after the graph, and
          it answered a question nobody was asking — "15 of 72" tells a client
          nothing about parts or service. The breadcrumb already says where
          the reader is, and that is the only position worth reporting. */}
      <div className="gr__hud">
        <div className="gr__hud-zoom">
          <button
            type="button"
            aria-label="Zoom out"
            onClick={() => setView((v) => ({ ...v, k: Math.max(ABS_MIN_K, v.k * 0.88) }))}
          >
            −
          </button>
          <button
            type="button"
            aria-label="Zoom in"
            onClick={() => setView((v) => ({ ...v, k: Math.min(1.8, v.k * 1.14) }))}
          >
            +
          </button>
          <button
            type="button"
            aria-label="Fit graph to view"
            onClick={() => setView(computeFit(size, layout, { allowSmall: true }))}
          >
            Fit
          </button>
          {/* Only offered once there is something to undo. */}
          {offsets.size > 0 && (
            <button
              type="button"
              aria-label="Put dragged nodes back where the layout placed them"
              onClick={resetPositions}
            >
              Reset
            </button>
          )}
          {/* The key sits with the other view controls rather than alone in
              the far corner, where it read as something left on the page by
              accident. It is a control for looking at the graph, which is
              what everything else in this group is. */}
          <button
            type="button"
            className={legendOpen ? 'is-on' : ''}
            aria-expanded={legendOpen}
            aria-label="Show what the shapes and lines mean"
            onClick={() => setLegendOpen((v) => !v)}
          >
            Key
          </button>
        </div>
      </div>

      <div className="gr__key">
        {legendOpen && (
          <div className="gr__key-body">
            <p className="gr__key-head">On screen</p>
            <ul className="gr__key-list">
              {legend.types.map((t) => (
                <li key={t} className="gr__key-row">
                  <span className={`gr__key-dot is-${t}`} aria-hidden="true" />
                  {NODE_TYPE_LABELS[t]}
                </li>
              ))}
            </ul>

            <p className="gr__key-head">Connectors</p>
            <ul className="gr__key-list">
              {legend.kinds.map((k) => (
                <li key={k} className="gr__key-row">
                  <svg className="gr__key-line" viewBox="0 0 26 6" aria-hidden="true">
                    <path className={`gr__edge is-${k}`} d="M 0 3 L 26 3" />
                  </svg>
                  {EDGE_KIND_LABELS[k]}
                </li>
              ))}
            </ul>

            {legend.flags.length > 0 && (
              <>
                <p className="gr__key-head">Marked on the box</p>
                <ul className="gr__key-list">
                  {legend.flags.map((f) => (
                    <li key={f} className="gr__key-row">
                      <svg className="gr__key-line" viewBox="0 0 26 8" aria-hidden="true">
                        <circle className={`gr__n-flag is-${f}`} cx={8} cy={4} r={3} />
                      </svg>
                      {CONFIDENCE_LABELS[f as keyof typeof CONFIDENCE_LABELS]}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/** What a connector means, for the key. */
const EDGE_KIND_LABELS: Readonly<Record<Edge['kind'], string>> = {
  flow: 'One step of a business process to the next',
  system: 'A step reaching the system that records it',
  integration: 'A system reaching outside the estate',
  data: 'A system writing a data entity',
}
