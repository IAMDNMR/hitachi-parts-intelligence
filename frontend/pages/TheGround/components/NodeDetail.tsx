import { CONFIDENCE_LABELS, NODE_TYPE_LABELS } from '../data/graph'
import type { GroundNode } from '../types/ground'

/**
 * WHAT THE SELECTED NODE ACTUALLY SAYS.
 *
 * Every node in this model has always carried more than its name. Twenty-two
 * of them carry a `detail` list — fifty-two lines describing the flows a
 * system sends, the segments a source diagram leaves unlabelled, the boxes it
 * marks with a question mark. Twelve carry a `facts` table lifted straight
 * from the client's canonical data model: which system masters an entity,
 * which only reference it, which third party it reaches. Six name the
 * reference diagram they came from.
 *
 * None of it had ever reached a screen. The graph was drawn from the same
 * file with those fields simply never read — roughly a third of the model's
 * substance, written down and invisible.
 *
 * WHY A PANEL BESIDE THE GRAPH AND NOT A CARD ON IT
 * -------------------------------------------------
 * There were detail cards here once and they were removed for a good reason:
 * they sat ON the canvas, over the thing the reader was working with, and
 * every one of them had to be dismissed before the map could be used again.
 * The words were never the problem. Their position was.
 *
 * So this takes its own column and the canvas takes what is left. Nothing is
 * ever covered; the graph re-fits itself into the narrower frame, which it
 * already knows how to do because it re-fits on every size change anyway.
 * Opening this costs width, and width is what the graph has spare — a branch
 * is drawn five to eight boxes wide down the middle of the screen.
 *
 * WHAT IT REFUSES TO DO
 * ---------------------
 * It does not invent a section to fill space. Twenty-three nodes carry
 * nothing beyond a summary — mostly the process steps, whose whole meaning is
 * their position in the chain — and for those this panel is deliberately
 * short rather than padded out with headings over empty lists.
 */
interface Props {
  node: GroundNode
  onClose: () => void
}

/**
 * Whether opening this node's panel is worth the click — the test behind the
 * dot on the Details button.
 *
 * Only `detail` and `facts` count. Provenance was in this test first, and it
 * made the signal useless: every node in the model carries a source or a
 * source reference, because that is the whole discipline of the file, so the
 * dot lit on all seventy-five and told the reader nothing. A marker that is
 * always on is not a marker.
 *
 * The caption in the bar already carries the summary and the role. What it
 * cannot carry is the four flow lines on a system, or a twelve-cell
 * system-of-record table on an entity, and those are exactly the thirty-odd
 * nodes worth pointing at.
 */
export function hasDeeperContent(node: GroundNode): boolean {
  return Boolean((node.detail && node.detail.length) || (node.facts && node.facts.length))
}

export function NodeDetail({ node, onClose }: Props) {
  const { detail, facts, provenance } = node

  return (
    <aside className="gr__panel" aria-label={`Detail for ${node.label}`}>
      <header className="gr__panel-head">
        <div className="gr__panel-ident">
          <p className="gr__panel-kind">{NODE_TYPE_LABELS[node.type]}</p>
          <h2 className="gr__panel-title">{node.label}</h2>
        </div>
        <button
          type="button"
          className="gr__panel-close"
          onClick={onClose}
          aria-label="Close detail"
        >
          ×
        </button>
      </header>

      <div className="gr__panel-body">
        <p className="gr__panel-summary">{node.summary}</p>

        {node.role && <p className="gr__panel-role">{node.role}</p>}

        {detail && detail.length > 0 && (
          <section className="gr__panel-section">
            <h3 className="gr__panel-heading">What it does</h3>
            <ul className="gr__panel-list">
              {detail.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
        )}

        {/* The system-of-record table, as the client's own data model states
            it. A blank cell is left blank and labelled — the source table has
            empty cells, and filling them in with a guess would be inventing
            an integration that may not exist. */}
        {facts && facts.length > 0 && (
          <section className="gr__panel-section">
            <h3 className="gr__panel-heading">Where it lives</h3>
            <dl className="gr__panel-facts">
              {facts.map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd className={fact.value ? undefined : 'is-blank'}>
                    {fact.value ?? 'Not stated in the source'}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        {/* Where this came from — the point of the whole provenance system,
            finally readable rather than hidden in a tooltip on a 3px dot. */}
        <section className="gr__panel-section gr__panel-prov">
          <h3 className="gr__panel-heading">How sure this is</h3>
          <p className={`gr__panel-confidence is-${provenance.confidence}`}>
            <span className="gr__panel-flag" aria-hidden="true" />
            {CONFIDENCE_LABELS[provenance.confidence]}
          </p>
          {provenance.source && <p className="gr__panel-source">{provenance.source}</p>}
          {provenance.sourceReference && (
            <p className="gr__panel-ref">{provenance.sourceReference}</p>
          )}
        </section>
      </div>
    </aside>
  )
}
