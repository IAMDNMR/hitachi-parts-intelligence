import { useCallback, useState } from 'react'
import '../styles/ground.css'

import { NODE_TYPE_LABELS, OPENING_ID, ORIGIN_ID, groundEdges, groundNodes } from '../data/graph'
import { useGraphState } from '../hooks/useGraphState'
import { GraphCanvas } from './GraphCanvas'
import { NodeDetail, hasDeeperContent } from './NodeDetail'

/**
 * THE GROUND.
 *
 * The complete Parts & Services ecosystem as one connected graph, read left
 * to right: the machine is sold, the relationship becomes after-sales,
 * after-sales runs through two domains — Parts and Service — each of which
 * runs a business process, each process is recorded in an enterprise
 * system, systems reach
 * outward through integration hubs to third parties, and the data those
 * systems hold resolves into a canonical model. Everything ends at uptime,
 * because that is what all of it is for.
 *
 * The graph is the experience. Clicking a node opens the layer beneath it and
 * lights the path through it; the flow labels appear on the lit path, and a
 * single caption line in the bar names what is selected.
 *
 * Beside it, and never over it, is the detail column — shut until asked for.
 * This used to read "there is no side panel and no card, because the graph
 * explains itself", which was true of the cards that were removed and untrue
 * of the model: a third of what the file says, including the system-of-record
 * table on every data entity and the reference diagram each claim came from,
 * had no way to reach the screen at all. The graph explains the SHAPE. The
 * column explains the claims. See NodeDetail.
 *
 * Business layers come from this project's own data; everything from the
 * systems column rightwards comes from two supplied reference diagrams,
 * including the points those diagrams themselves mark uncertain. See
 * src/ground/data/graph.ts for what each node and edge claims.
 */
/**
 * The nodes the parts-ordering service actually implements.
 *
 * Selecting any of them means the reader is looking at a step this project
 * has built a working tool for, so that is where the offer to open it
 * appears — not on every node, which would be an advert rather than a link,
 * and not only on Parts Ordering itself, which is one step of seven.
 */
const ORDERING_NODES = new Set([
  'parts',
  'p-requirement',
  'p-identification',
  'p-availability',
  'p-ordering',
  'p-inventory',
  'p-shipment',
  'p-goods-receipt',
])

interface Props {
  onHome: () => void
  onOpenOrdering: () => void
}

export function TheGround({ onHome, onOpenOrdering }: Props) {
  const state = useGraphState(groundNodes, groundEdges, ORIGIN_ID, OPENING_ID)

  /**
   * Whether the detail column is showing.
   *
   * Shut on the first view, and it stays however the reader leaves it. The
   * opening screen is composed — a spine and two domains, sized to the whole
   * frame — and taking a third of its width away before anyone has asked a
   * question would be answering one nobody had. Once it is open it stays
   * open, because a reader who wanted the detail on one node wants it on the
   * next one too.
   */
  const [detailOpen, setDetailOpen] = useState(false)
  const selected = state.selected
  const hasDetail = selected ? hasDeeperContent(selected) : false

  const home = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      onHome()
    },
    [onHome],
  )

  const ordering = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      onOpenOrdering()
    },
    [onOpenOrdering],
  )

  return (
    <div className="ground">
      <header className="header">
        <a className="header__brand" href="#" onClick={home}>
          <span className="header__brand-main">HITACHI</span>
          <span className="header__brand-sub">AFTER-SALES</span>
        </a>
        <nav className="header__nav" aria-label="Sections">
          <span className="header__link is-current" aria-current="page">
            The Ground
          </span>
          {/* In the header, not only on the Parts branch.
              The contextual button below appears once a reader has drilled
              into Parts — which is useless for finding the tool in the first
              place, because it is invisible until you already know where it
              is. This is the way in; that one is the shortcut once you are
              standing on the process it runs. */}
          <a className="header__link" href="#/parts-ordering" onClick={ordering}>
            Parts Ordering
          </a>
        </nav>
      </header>

      <main className="gr">
        <div className="gr__bar">
          <div className="gr__titles">
            <h1 className="gr__title">Parts &amp; Services</h1>
            {/* The route the reader has taken, rather than a fixed strapline.
                Opening a node closes the branches beside it, so this is the
                only place the way back is written down — and every step of it
                is a way back. */}
            <nav className="gr__trail" aria-label="Path to the selected node">
              {state.trail.map((n, i) => (
                <span className="gr__trail-item" key={n.id}>
                  {i > 0 && (
                    <span className="gr__trail-sep" aria-hidden="true">
                      /
                    </span>
                  )}
                  <button
                    type="button"
                    className="gr__trail-step"
                    aria-current={n.id === state.selectedId ? 'true' : undefined}
                    onClick={() => state.activate(n.id)}
                  >
                    {n.label}
                  </button>
                </span>
              ))}
            </nav>

            {/* What is selected, in a sentence.
                Every node in this model carries a summary and most carry a
                role, and until now none of it reached the screen — the detail
                cards that used to hold it were removed because they sat on
                top of the graph and got in the way of the workflow. The words
                were never the problem. They live in the bar instead, on the
                page's own furniture, where they read as a caption to the map
                rather than as a panel over it. */}
          </div>

          <div className="gr__controls">
            {/* There is deliberately no "expand all". Opening everything at
                once is the state this page was rebuilt to avoid: it puts
                sixty-eight nodes across nineteen layers on a canvas that can
                hold about seven, and every reading of it needs a zoom control
                to recover from. The map is read by following one path. */}
            <button
              type="button"
              className="gr__btn"
              onClick={state.reset}
              disabled={state.atOpening}
            >
              Start over
            </button>

            {/* The way into everything the model knows and the canvas has no
                room to print. The dot marks the nodes carrying a detail list
                or a fact table — every system, hub and third party, and all
                twelve data entities — so the control advertises itself where
                opening it is worth the click. See hasDeeperContent for why
                provenance deliberately does not count towards that. */}
            <button
              type="button"
              className={`gr__btn gr__btn--detail${detailOpen ? ' is-on' : ''}`}
              aria-pressed={detailOpen}
              onClick={() => setDetailOpen((v) => !v)}
            >
              Details
              {hasDetail && !detailOpen && (
                <span className="gr__btn-dot" aria-label="more on this node" />
              )}
            </button>
            {/* Only where there is something to open — see ORDERING_NODES. */}
            {state.selectedId && ORDERING_NODES.has(state.selectedId) && (
              <button
                type="button"
                className="gr__btn gr__btn--go"
                onClick={onOpenOrdering}
              >
                Open Parts Ordering →
              </button>
            )}
            <a className="gr__btn gr__btn--ghost" href="#" onClick={home}>
              ← Home
            </a>
          </div>

          {/* One line, under both. It names what is selected and what kind of
              thing it is — the words the node itself no longer prints. */}
          {state.selected && (
            <p className="gr__caption">
              <span className="gr__caption-kind">
                {NODE_TYPE_LABELS[state.selected.type]}
              </span>
              <span className="gr__caption-main">{state.selected.summary}</span>
              {state.selected.role && (
                <span className="gr__caption-role">{state.selected.role}</span>
              )}
            </p>
          )}
        </div>

        {/* The canvas and the detail column share the row. The panel is not
            laid over the graph — that is what the old detail cards did, and
            why they were taken out. The graph gives up width and re-fits
            itself into what is left, which costs it nothing it was using: a
            branch is five to eight boxes wide in a frame built for far more. */}
        <div className="gr__body">
          <div className="gr__stage">
            <GraphCanvas nodes={groundNodes} edges={groundEdges} state={state} />
          </div>

          {detailOpen && selected && (
            <NodeDetail node={selected} onClose={() => setDetailOpen(false)} />
          )}
        </div>
      </main>
    </div>
  )
}
