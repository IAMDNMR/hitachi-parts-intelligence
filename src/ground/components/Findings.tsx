import { useCallback, useMemo } from 'react'
import '../styles/findings.css'

import { CONFIDENCE_LABELS, groundEdges, groundNodes } from '../data/graph'
import {
  FINDING_MEANING,
  FINDING_ORDER,
  collectFindings,
  countConfidence,
} from '../data/findings'
import type { OpenConfidence } from '../data/findings'

/**
 * ARCHITECTURE FINDINGS.
 *
 * The map, read as a document rather than as a picture.
 *
 * Everything here comes out of the same provenance the graph draws its marks
 * from — see data/findings.ts — so the two cannot disagree. What changes is
 * the reading. On the canvas a confidence mark is a caveat on one box, found
 * only by hovering the box you already happened to be looking at. Gathered
 * into a list it becomes the thing this project can hand a client that they
 * could not have produced themselves: every question their own architecture
 * documentation does not answer, with the reasoning attached.
 *
 * Each finding links to the node on the map, so the document and the diagram
 * are two views of one model rather than two deliverables to keep in step.
 *
 * It prints. That is the export — a page laid out for paper reaches a client
 * as a PDF through the browser they already have, and needs no library and no
 * server to render one.
 */
interface Props {
  onHome: () => void
  onOpenGround: (nodeId?: string) => void
}

export function Findings({ onHome, onOpenGround }: Props) {
  const findings = useMemo(() => collectFindings(groundNodes, groundEdges), [])
  const counts = useMemo(() => countConfidence(groundNodes, groundEdges), [])

  const grouped = useMemo(
    () =>
      FINDING_ORDER.map((confidence) => ({
        confidence,
        items: findings.filter((f) => f.confidence === confidence),
      })).filter((g) => g.items.length > 0),
    [findings],
  )

  const home = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      onHome()
    },
    [onHome],
  )

  const ground = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      onOpenGround()
    },
    [onOpenGround],
  )

  const confirmedShare = Math.round((counts.confirmed / counts.total) * 100)

  return (
    <div className="ground">
      <header className="header fnd__chrome">
        <a className="header__brand" href="#" onClick={home}>
          <span className="header__brand-main">HITACHI</span>
          <span className="header__brand-sub">AFTER-SALES</span>
        </a>
        <nav className="header__nav" aria-label="Sections">
          <a className="header__link" href="#/the-ground" onClick={ground}>
            The Ground
          </a>
          <span className="header__link is-current" aria-current="page">
            Findings
          </span>
        </nav>
      </header>

      <main className="fnd">
        <header className="fnd__head">
          <p className="fnd__eyebrow">Parts &amp; Services · Architecture Review</p>
          <h1 className="fnd__title">What the supplied material does not answer</h1>
          <p className="fnd__standfirst">
            Every claim in the Parts &amp; Services model that is not confirmed by the documents
            we were given, with what it rests on. Derived from the model itself, so this list
            and the map cannot disagree.
          </p>

          <div className="fnd__tally">
            <div>
              <dt>Claims in the model</dt>
              <dd>{counts.total}</dd>
            </div>
            <div>
              <dt>Confirmed by supplied material</dt>
              <dd>
                {counts.confirmed}
                <span className="fnd__tally-sub">{confirmedShare}%</span>
              </dd>
            </div>
            <div className="is-open">
              <dt>Open questions</dt>
              <dd>{counts.open}</dd>
            </div>
          </div>

          <button type="button" className="fnd__print" onClick={() => window.print()}>
            Print or save as PDF
          </button>
        </header>

        {/* The method, before the findings. A list of things somebody is
            unsure about is worth nothing until the reader knows what the
            grades mean and who applied them. */}
        <section className="fnd__method">
          <h2 className="fnd__h2">Method</h2>
          <p>
            The business layers of the model come from this project's own material. Everything
            from the enterprise systems onward comes from two supplied reference diagrams:
            an EDI and ERP topology, and a Parts canonical data model. Each node and each
            relationship was graded as it was drawn, and the grades below are those gradings
            collected — nothing was assessed a second time for this document.
          </p>
          <dl className="fnd__grades">
            {FINDING_ORDER.filter((c) => grouped.some((g) => g.confidence === c)).map((c) => (
              <div key={c}>
                <dt>
                  <span className={`fnd__dot is-${c}`} aria-hidden="true" />
                  {CONFIDENCE_LABELS[c]}
                </dt>
                <dd>{FINDING_MEANING[c]}</dd>
              </div>
            ))}
          </dl>
        </section>

        {grouped.map((group) => (
          <section className="fnd__group" key={group.confidence}>
            <header className="fnd__group-head">
              <h2 className="fnd__h2">
                <span className={`fnd__dot is-${group.confidence}`} aria-hidden="true" />
                {CONFIDENCE_LABELS[group.confidence as OpenConfidence]}
              </h2>
              <span className="fnd__group-count">
                {group.items.length} {group.items.length === 1 ? 'finding' : 'findings'}
              </span>
            </header>

            <ol className="fnd__list">
              {group.items.map((f) => (
                <li className="fnd__item" key={f.key}>
                  <div className="fnd__item-head">
                    <h3 className="fnd__item-title">{f.title}</h3>
                    <span className="fnd__item-about">{f.about}</span>
                  </div>
                  <p className="fnd__claim">{f.claim}</p>
                  {f.basis && <p className="fnd__basis">{f.basis}</p>}
                  {f.sourceReference && <p className="fnd__ref">{f.sourceReference}</p>}
                  <button
                    type="button"
                    className="fnd__locate"
                    onClick={() => onOpenGround(f.nodeId)}
                  >
                    Show on the map
                  </button>
                </li>
              ))}
            </ol>
          </section>
        ))}

        <footer className="fnd__foot">
          <p>
            Generated from the Parts &amp; Services model — {groundNodes.length} nodes and{' '}
            {groundEdges.length} relationships. Every finding above is a grading carried by the
            model itself; correcting one in the model corrects it here.
          </p>
        </footer>
      </main>
    </div>
  )
}
