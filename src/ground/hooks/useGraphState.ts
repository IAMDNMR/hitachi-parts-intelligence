import { useCallback, useMemo, useState } from 'react'
import type { Edge, GroundNode } from '../types/ground'

/**
 * What is on the canvas, what is selected, and what lights up.
 *
 * EXPANSION COMES FROM THE RELATIONSHIPS
 * --------------------------------------
 * It used to come from `revealedBy`, a list written by hand on each node
 * naming the parent that brings it onto the canvas. That is a tree, and the
 * model is a mesh, so the two disagreed in fifty-two places — fifty-two real
 * relationships that could not be reached by clicking either end of them:
 *
 *   Uptime            four things feed it; none of them could open it, and
 *                     nothing opened Uptime, so it sat alone at the bottom
 *                     of the picture with no visible relationship at all.
 *   Repair            seven neighbours, one of them reachable. Service
 *                     History, Parts Requirement and Warranty were not.
 *   Warranty          its links into Parts Ordering and Repair — the whole
 *                     reason warranty is not a silo — were unreachable.
 *   Monitoring        the flagship cross-link in the model, machine data
 *                     raising a parts requirement, could not be opened.
 *   Sales & Handover  revealed Delivery and Handover, which it has no edge
 *                     to: two nodes appearing with no relationship shown.
 *
 * Clicking a node now shows what that node is connected to, in both
 * directions, taken from `groundEdges`. There is only one statement of the
 * graph, so the picture cannot contradict it.
 *
 * WHAT IS ON SCREEN
 * -----------------
 * The route from the start of the story to the selection, plus everything
 * the selection touches. Following a branch keeps the page about one chain
 * wide however deep the model goes, and every step of the way back is on
 * screen as the breadcrumb.
 */

export interface GraphState {
  visible: Set<string>
  selectedId: string | null
  selected: GroundNode | null
  /** Ids on the traced path from the selection. */
  litNodes: Set<string>
  /** Indices into the edge array that are on the traced path. */
  litEdges: Set<number>
  /** Selects a node and brings what it connects to onto the canvas. */
  activate: (id: string) => void
  reset: () => void
  /** True when this node touches something not currently drawn. */
  isExpandable: (id: string) => boolean
  /** How many of its neighbours are not on the canvas yet. */
  revealCount: (id: string) => number
  /** True when everything this node touches is already drawn. */
  isOpen: (id: string) => boolean
  /** The route from the start of the story to the selection. */
  trail: GroundNode[]
  /**
   * Ids on the route the reader walked.
   *
   * Everything else on the canvas is there because the node in hand touches
   * it — often from another domain entirely, which is the model being honest
   * and, without this, looks like the picture changing subject. Marking the
   * route lets the two be told apart at a glance.
   */
  onPath: Set<string>
  /** True when the reader has not gone anywhere yet. */
  atOpening: boolean
}

/**
 * How many steps of the route are drawn on the canvas, counting the selection
 * itself. The rest is on the breadcrumb, which is always visible.
 *
 * This was four, and four is too few. The route is the reader's anchor — it
 * is the only part of the picture that says where they are — and at four it
 * eroded from the top as they went deeper: Machine Sold dropped off on the
 * second click, Sales & Handover on the third. Every click changed the top of
 * the picture as well as the bottom, which is most of why drilling in felt
 * like being shown a different diagram each time rather than going further
 * into one.
 *
 * Six holds the whole spine — machine sold, sales, after-sales, a domain, a
 * process and the step in hand — through the drills that matter.
 */
const ROUTE_ON_CANVAS = 6

export function useGraphState(
  nodes: readonly GroundNode[],
  edges: readonly Edge[],
  rootId: string,
  /**
   * Where the page opens.
   *
   * Not the root. The story starts at the machine being sold, but the thing
   * this page is about is what happens afterwards, and opening on the root
   * showed three boxes — a sale, a customer and a handover — with none of
   * the ecosystem in sight. Opening on After-Sales puts the spine above it
   * and its two domains below it, so the first thing on screen is the point
   * everything expands from.
   */
  openingId: string = rootId,
): GraphState {
  /**
   * The reader's own path, kept as a path rather than recomputed from the
   * selection.
   *
   * The route used to be derived each time as the SHORTEST way from the start
   * of the story to whatever was selected, and that quietly rewrote history.
   * Walking Parts → Parts Requirement → Part Identification → Parts
   * Availability → Parts Ordering, the last step has a four-hop route through
   * Warranty and a seven-hop one through the parts chain, so the shorter one
   * won: three of the steps the reader had just walked vanished from the
   * canvas and Warranty appeared in their place. Nothing had gone wrong, and
   * it looked like a different diagram.
   *
   * A path the reader built by walking it does not do that. It grows by one
   * when they go somewhere connected, shortens when they step back to
   * something already on it, and is only recomputed when they jump.
   */
  const [path, setPath] = useState<string[]>(() => [rootId])

  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])

  /** id → everything it touches, in both directions. */
  const neighbours = useMemo(() => {
    const map = new Map<string, Set<string>>()
    const add = (a: string, b: string) => {
      const set = map.get(a)
      if (set) set.add(b)
      else map.set(a, new Set([b]))
    }
    edges.forEach((e) => {
      if (e.from === e.to) return
      add(e.from, e.to)
      add(e.to, e.from)
    })
    return map
  }, [edges])

  /** id → what it feeds, for walking the story forwards. */
  const downstream = useMemo(() => {
    const map = new Map<string, string[]>()
    edges.forEach((e) => {
      if (e.from === e.to) return
      const list = map.get(e.from)
      if (list) list.push(e.to)
      else map.set(e.from, [e.to])
    })
    return map
  }, [edges])

  /**
   * The shortest way from the start of the story to a node, following the
   * direction of flow. Used only when the reader arrives somewhere that is
   * not a step from where they were — the opening, a reset, or a jump.
   */
  const routeTo = useCallback(
    (target: string): string[] => {
      if (target === rootId) return [rootId]

      /* The search runs to exhaustion rather than stopping at the target.
         It used to break the moment it found what it was looking for, which
         is faster and leaves `cameFrom` half-built — no use at all to the
         fallback below, which needs to know how far the root reaches. The
         graph is 75 nodes; walking all of it costs nothing measurable. */
      const cameFrom = new Map<string, string | null>([[rootId, null]])
      const queue = [rootId]
      while (queue.length) {
        const at = queue.shift() as string
        for (const to of downstream.get(at) ?? []) {
          if (cameFrom.has(to)) continue
          cameFrom.set(to, at)
          queue.push(to)
        }
      }

      /** Reads a finished path out of the search above. */
      const trace = (to: string): string[] => {
        const path: string[] = []
        let at: string | null | undefined = to
        while (at) {
          path.unshift(at)
          at = cameFrom.get(at)
        }
        return path
      }

      if (!cameFrom.has(target)) {
        /**
         * Nothing downstream reaches it.
         *
         * Four nodes are like this: the start of the story, and Machine Data,
         * Warranty and the dealer Network. They are not steps in the flow,
         * they are INPUTS to it — a warranty covers a repair, monitoring
         * raises a requirement — so no path that follows the direction of
         * flow arrives at them.
         *
         * This used to return the node on its own, which the comment above it
         * described as walking back up and did not do. The effect was a
         * breadcrumb reading only "Warranty": no spine, no context, and on a
         * deep link that was the entire trail. The reader landed on a box
         * with nothing saying where it sat.
         *
         * So route to the nearest thing it FEEDS — which is reachable — and
         * put the node on the end. The trail then reads
         * "… / Service / Repair / Warranty", which is how the reader got
         * there and what the node relates to. The direction is never
         * misstated: the canvas still draws the arrow from Warranty into
         * Repair, because that comes from the edge, not from this.
         */
        /* Walk forward from the orphan until something the root CAN reach
           turns up, and anchor the trail there.

           Its immediate children are not always enough. Warranty feeds
           Repair, which is one step and reachable, so that one is easy.
           Machine Data feeds an entire chain of its own — information,
           status, monitoring — none of which the flow reaches either, and
           the first reachable thing is four steps down where monitoring
           raises a parts requirement. Looking only one step ahead left
           Machine Data with a breadcrumb reading "Machine Data" and nothing
           else, which is the state this whole fallback exists to avoid. */
        const seen = new Set<string>([target])
        const ahead = [...(downstream.get(target) ?? [])]
        let best: string[] | null = null
        while (ahead.length) {
          const at = ahead.shift() as string
          if (seen.has(at)) continue
          seen.add(at)
          if (cameFrom.has(at)) {
            /* Among every reachable descendant, the one with the SHORTEST
               route from the start of the story wins — not the one fewest
               steps from the orphan. Those differ: the dealer network feeds
               the Dealer directly, but the Dealer is twelve steps down the
               parts chain, while the Technician it also feeds reaches Repair
               in six. Both are true relationships, and six steps is a
               breadcrumb somebody can read. */
            const via = trace(at)
            if (!best || via.length < best.length) best = via
            // Anything past a reachable node is reachable too, and further
            // from the story — nothing below it can beat it.
            continue
          }
          ahead.push(...(downstream.get(at) ?? []))
        }
        return best ? [...best, target] : [target]
      }

      return trace(target)
    },
    [rootId, downstream],
  )

  /* The path is seeded once the graph is known, so the page opens on
     After-Sales with the spine above it. */
  const route = useMemo(() => {
    if (path.length > 1 || path[0] !== rootId) return path
    return routeTo(openingId)
  }, [path, routeTo, rootId, openingId])

  const selectedId = route.length ? (route[route.length - 1] as string) : rootId

  /**
   * How much of the route is drawn.
   *
   * All of it used to be, and past about five levels the top of it was
   * off the canvas: the camera holds a readable scale rather than shrinking
   * to fit, so at the systems layer Machine Sold, Sales & Handover and
   * After-Sales were being laid out, connected and painted somewhere beyond
   * the edge of the frame. They cost the graph a third of its height and
   * nobody could see them.
   *
   * The breadcrumb carries the whole route, always, and every step of it is
   * a way back. The canvas carries the part of it that is still context for
   * what is in hand.
   */
  const drawnRoute = useMemo(
    () => (route.length > ROUTE_ON_CANVAS ? route.slice(-ROUTE_ON_CANVAS) : route),
    [route],
  )

  /**
   * The canvas: the route here, and everything the selection touches.
   *
   * At the very start there is no branch to follow yet, so Parts and
   * Service are brought on as the choice they are — otherwise the opening
   * view would be a single box. Machine Data, Warranty and the dealer
   * network are not offered here: they are not entry points, they are what
   * Parts and Service reach into once the reader is inside one of them.
   */
  const visible = useMemo(() => {
    const set = new Set<string>(drawnRoute)
    if (!selectedId) return set

    /* The opening is the one view that is composed rather than explored, so
       it is built forwards only: the spine down to after-sales, and the five
       domains it opens onto.
       
       Taking every neighbour here instead put Handover on screen beside Sales
       & Handover — a real relationship, but two nodes a character apart in
       name, at different levels, in the one picture that has to say plainly
       what this page is about. It is one click away under Sales & Handover.

       The shortest route also skips the customer, who is not an optional
       detail of "a machine is sold to a customer", so the root's own next
       step is added as well. */
    if (selectedId === openingId) {
      downstream.get(rootId)?.forEach((id) => set.add(id))
      downstream.get(selectedId)?.forEach((id) => set.add(id))
      return set
    }

    neighbours.get(selectedId)?.forEach((id) => set.add(id))
    return set
  }, [drawnRoute, selectedId, neighbours, downstream, openingId, rootId])

  const { litNodes, litEdges } = useMemo(() => {
    const litN = new Set<string>()
    const litE = new Set<number>()
    if (!selectedId || !visible.has(selectedId)) return { litNodes: litN, litEdges: litE }

    litN.add(selectedId)
    edges.forEach((edge, index) => {
      if (!visible.has(edge.from) || !visible.has(edge.to)) return
      if (edge.from !== selectedId && edge.to !== selectedId) return
      litE.add(index)
      litN.add(edge.from)
      litN.add(edge.to)
    })
    return { litNodes: litN, litEdges: litE }
  }, [selectedId, edges, visible])

  const revealCount = useCallback(
    (id: string) => {
      const near = neighbours.get(id)
      if (!near) return 0
      let n = 0
      near.forEach((o) => {
        if (!visible.has(o)) n++
      })
      return n
    },
    [neighbours, visible],
  )

  const isExpandable = useCallback((id: string) => revealCount(id) > 0, [revealCount])
  const isOpen = useCallback(
    (id: string) => (neighbours.get(id)?.size ?? 0) > 0 && revealCount(id) === 0,
    [neighbours, revealCount],
  )

  /**
   * Going somewhere.
   *
   * Three cases, and the order matters. Stepping back onto something already
   * on the path shortens it to there. Stepping onto something connected to
   * where they are extends it by one — which is what keeps the canvas showing
   * the route they actually walked. Anything else is a jump, and only then is
   * a route computed for them.
   */
  const activate = useCallback(
    (id: string) => {
      setPath((prev) => {
        const here = prev.length > 1 || prev[0] !== rootId ? prev : routeTo(openingId)
        const at = here.indexOf(id)
        if (at >= 0) return here.slice(0, at + 1)
        const last = here[here.length - 1]
        if (last && neighbours.get(last)?.has(id)) return [...here, id]
        return routeTo(id)
      })
    },
    [routeTo, neighbours, rootId, openingId],
  )

  const reset = useCallback(() => {
    setPath(routeTo(openingId))
  }, [routeTo, openingId])

  const selected = selectedId ? (nodeById.get(selectedId) ?? null) : null

  const trail = useMemo(
    () => route.map((id) => nodeById.get(id)).filter((n): n is GroundNode => Boolean(n)),
    [route, nodeById],
  )

  return {
    onPath: new Set(route),
    atOpening: selectedId === openingId,
    visible,
    selectedId,
    selected,
    litNodes,
    litEdges,
    activate,
    reset,
    isExpandable,
    revealCount,
    isOpen,
    trail,
  }
}
