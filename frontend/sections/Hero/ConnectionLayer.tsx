import { useRef, useState, type MutableRefObject, type RefObject } from 'react'
import { ecosystemNodes, CONNECTIONS_FADE_OUT, type EcosystemNode } from '../../data/ecosystemNodes'
import { ramp, stageScale } from '../../data/storyStates'
import { useProgressEffect } from '../../hooks/progressStore'
import { useStageFit, anchorToStage, cardToStage, type Point, type StageFit } from '../../hooks/useStageFit'
import { NodeIcon } from './Icons'

/** How long one connection takes to draw itself, in progress units. */
const DRAW_SPAN = 0.05

interface ConnectionLayerProps {
  stageRef: RefObject<HTMLElement | null>
  boxRef: RefObject<HTMLElement | null>
  mediaRef: MutableRefObject<HTMLCanvasElement | null>
  openNodeId: string | null
  onOpenNode: (id: string) => void
}

/**
 * The connection layer: machine component → path → label.
 *
 * Every line starts on an actual component of the separated machine. Anchors
 * are stored in the clip's own frame coordinates and converted to stage pixels
 * here, so they stay on their component at any viewport size and through the
 * camera move. Nothing on this layer is decorative — if a line is drawn,
 * it connects two specific things.
 */
export function ConnectionLayer({ stageRef, boxRef, mediaRef, openNodeId, onOpenNode }: ConnectionLayerProps) {
  const groupRef = useRef<HTMLDivElement>(null)
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const pathRefs = useRef<Record<string, SVGPathElement | null>>({})
  const dotRefs = useRef<Record<string, SVGCircleElement | null>>({})
  const [hovered, setHovered] = useState<string | null>(null)
  const fit = useStageFit(stageRef, boxRef, mediaRef)

  useProgressEffect((p) => {
    const group = groupRef.current
    if (!group || !fit) return

    const groupOpacity =
      1 - ramp(p, CONNECTIONS_FADE_OUT[0]!, CONNECTIONS_FADE_OUT[1]!)
    group.style.opacity = groupOpacity.toFixed(3)
    group.style.visibility = groupOpacity < 0.01 ? 'hidden' : 'visible'
    if (groupOpacity < 0.01) return

    const scale = stageScale()

    ecosystemNodes.forEach((node) => {
      const draw = ramp(p, node.reveal, node.reveal + DRAW_SPAN)

      const points = routePoints(fit, node, scale)
      const path = pathRefs.current[node.id]
      if (path) {
        // The geometry is rebuilt every frame because the machine is moving
        // under it; the reveal itself is a dash offset, which the compositor
        // can animate without re-measuring the path.
        path.setAttribute('d', toPath(points))
        const length = pathLength(points)
        path.style.strokeDasharray = `${length}`
        path.style.strokeDashoffset = `${length * (1 - draw)}`
      }

      const dot = dotRefs.current[node.id]
      if (dot) {
        dot.setAttribute('cx', points[0].x.toFixed(1))
        dot.setAttribute('cy', points[0].y.toFixed(1))
        dot.style.opacity = (draw > 0.02 ? 1 : 0).toString()
      }

      // The label arrives once its line has reached it.
      const arrive = ramp(p, node.reveal + DRAW_SPAN * 0.7, node.reveal + DRAW_SPAN * 1.4)
      const card = cardRefs.current[node.id]
      if (card) {
        card.style.opacity = arrive.toFixed(3)
        card.style.transform = `translate(-50%, ${((1 - arrive) * 8).toFixed(2)}px)`
        card.style.visibility = arrive < 0.01 ? 'hidden' : 'visible'
      }
    })
  })

  if (!fit) return <div className="connections" ref={groupRef} />

  return (
    <div className="connections" ref={groupRef}>
      <svg
        className="connections__svg"
        viewBox={`0 0 ${fit.stageW} ${fit.stageH}`}
        width={fit.stageW}
        height={fit.stageH}
        aria-hidden="true"
        focusable="false"
      >
        {ecosystemNodes.map((node) => (
          <g
            key={node.id}
            className="connections__group"
            data-active={hovered === node.id || openNodeId === node.id}
          >
            <path
              className="connections__path"
              ref={(el) => {
                pathRefs.current[node.id] = el
              }}
              d=""
            />
            <circle
              className="connections__origin"
              ref={(el) => {
                dotRefs.current[node.id] = el
              }}
              r="2.5"
            />
          </g>
        ))}
      </svg>

      {ecosystemNodes.map((node) => {
        const point = cardToStage(fit, node.card)
        return (
          <div
            className="connections__card"
            key={node.id}
            style={{ left: `${point.x}px`, top: `${point.y}px` }}
            ref={(el) => {
              cardRefs.current[node.id] = el
            }}
          >
            <button
              type="button"
              className="card"
              data-open={openNodeId === node.id}
              aria-expanded={openNodeId === node.id}
              onClick={() => onOpenNode(node.id)}
              onPointerEnter={() => setHovered(node.id)}
              onPointerLeave={() => setHovered((v) => (v === node.id ? null : v))}
              onFocus={() => setHovered(node.id)}
              onBlur={() => setHovered((v) => (v === node.id ? null : v))}
            >
              <span className="card__icon">
                <NodeIcon name={node.icon} />
              </span>
              <span className="card__text">
                <span className="card__label">{node.label}</span>
                <span className="card__component">{node.component}</span>
              </span>
            </button>
          </div>
        )
      })}
    </div>
  )
}

/**
 * An orthogonal route from the component down to its label: drop, step
 * across, drop again. Right angles read as an engineering callout; a curve
 * would read as decoration.
 */
function routePoints(fit: StageFit, node: EcosystemNode, scale: number): [Point, Point, Point, Point] {
  const anchor = anchorToStage(fit, node.anchor, scale)
  const card = cardToStage(fit, node.card)
  const cardTop = card.y - 12
  const bend = anchor.y + (cardTop - anchor.y) * 0.62

  return [
    anchor,
    { x: anchor.x, y: bend },
    { x: card.x, y: bend },
    { x: card.x, y: cardTop },
  ]
}

/** The polyline as an SVG path. */
function toPath(points: Point[]): string {
  return points
    .map((p, i) => `${i ? 'L' : 'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ')
}

/** Total length of the polyline, for the dash reveal. */
function pathLength(points: Point[]): number {
  let total = 0
  for (let i = 1; i < points.length; i += 1) {
    const curr = points[i]
    const prev = points[i - 1]
    if (!curr || !prev) continue
    total += Math.hypot(curr.x - prev.x, curr.y - prev.y)
  }
  return total
}
