import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'

import { machinesInCategory, type Category } from '../../data/machineCatalogue'
import { infoRows, nameParts, storyLine, type InfoRow } from './showcase'

/**
 * THE MODEL SHOWCASE — one category, one machine at a time.
 *
 * A tall track with a 100vh viewport pinned inside it. The page scrolls
 * normally; how far the track has been scrolled picks which machine is in the
 * viewport. Each machine owns an equal interval of that distance, so a wheel
 * tick moves a little way through an interval and a machine only changes when
 * its interval is crossed. There is no wheel handler, no snapping and no inner
 * scrollbar - mouse, trackpad, touch and keyboard all work because it is just
 * the page scrolling. When the last interval ends the track ends, the pin
 * releases, and the page carries on.
 *
 * The same component serves all seven categories: it is handed a category and
 * reads that category's machines from the catalogue. The count, the names, the
 * facts and the pictures all come from the data.
 */

/** Scroll distance each machine owns, as a share of the viewport height. */
const STEP_VH = 55

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const pad = (n: number) => String(n).padStart(2, '0')

/* One orange line mark per fact, drawn in the 24px, 1.6-stroke style the
   section's other icons use. Keyed by the row keys infoRows() produces. */
const icon = (children: ReactNode) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

const ROW_ICONS: Record<string, ReactNode> = {
  // four blocks: which family of machine
  category: icon(
    <>
      <rect x="4" y="4" width="6.5" height="6.5" rx="1" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="1" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="1" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1" />
    </>,
  ),
  // a tag: the model code
  model: icon(
    <>
      <path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7l8.3 8.3a1 1 0 0 1 0 1.4l-7.3 7.3a1 1 0 0 1-1.4 0z" />
      <circle cx="8.2" cy="8.2" r="1.4" />
    </>,
  ),
  // a weight
  weight: icon(
    <>
      <circle cx="12" cy="6" r="2.4" />
      <path d="M7.2 9h9.6l3 11.5H4.2z" />
    </>,
  ),
  // a bolt: power and drive
  power: icon(<path d="M13 2.5 5 13.5h6l-1 8 8-11h-6l1-8z" />),
}

interface ModelShowcaseProps {
  category: Category
  onOpenMachine: (id: string) => void
  onBack: () => void
  resumeId: string | null
}

export function ModelShowcase({ category, onOpenMachine, onBack, resumeId }: ModelShowcaseProps) {
  const machines = useMemo(
    () =>
      machinesInCategory(category.id).map((m) => {
        const parts = nameParts(m)
        return {
          machine: m,
          ...parts,
          // The longest unbreakable run in the name - a model code is never split
          // across lines, so the type is sized so that run fits the column.
          chars: Math.max(...parts.name.split(/\s+/).map((t) => t.length)),
          story: storyLine(m, category),
          rows: infoRows(m),
        }
      }),
    [category],
  )
  const n = machines.length
  const resumeAt = Math.max(0, machines.findIndex((x) => x.machine.id === resumeId))

  const track = useRef<HTMLDivElement>(null)
  const [index, setIndex] = useState(resumeAt)

  /* Where the track is, read once per frame at most. The index lives in state
     because the whole view changes with it; the finer progress only moves a
     line, so it is written straight to a CSS variable and never re-renders. */
  useEffect(() => {
    let frame = 0
    const read = () => {
      frame = 0
      const el = track.current
      if (!el) return
      const box = el.getBoundingClientRect()
      const run = box.height - window.innerHeight
      const p = run > 0 ? Math.min(1, Math.max(0, -box.top / run)) : 0
      el.style.setProperty('--mc-show-p', p.toFixed(4))
      setIndex(Math.min(n - 1, Math.floor(p * n)))
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(read)
    }
    read()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [n])

  /** Scroll the page to the middle of machine i's interval. */
  const goTo = useCallback(
    (i: number, instant = false) => {
      const el = track.current
      if (!el) return
      const k = Math.min(n - 1, Math.max(0, i))
      const top = el.getBoundingClientRect().top + window.scrollY
      const run = el.offsetHeight - window.innerHeight
      window.scrollTo({ top: top + (run * (k + 0.5)) / n, behavior: instant || reducedMotion() ? 'auto' : 'smooth' })
    },
    [n],
  )

  /* Coming back from a machine's own page: put the reader on that machine
     again, not on the first one. */
  useLayoutEffect(() => {
    if (resumeId && resumeAt > 0) goTo(resumeAt, true)
    // Only on arrival; later scrolling is the reader's.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cur = machines[index]!
  const place = (i: number) => (i < index ? ' is-past' : i > index ? ' is-next' : ' is-on')

  return (
    <div
      className="mc-show"
      ref={track}
      style={{ height: `calc(100vh + ${Math.max(0, n - 1) * STEP_VH}vh)` }}
      aria-roledescription="machine showcase"
      aria-label={`${category.subcategoryLabel}, ${n} machines`}
    >
      <div className="mc-show__pin">
        <div className="mc-show__ground" aria-hidden="true" />
        <span className="mc-show__arc" aria-hidden="true" />

        <div className="mc-show__stage">
          {/* ---- left: where you are, and which machine ---- */}
          <div className="mc-show__story">
            <button className="mc-show__back" type="button" onClick={onBack}>
              <span aria-hidden="true">←</span> All machinery
            </button>
            <span className="mc-show__rule" aria-hidden="true" />
            <p className="mc-show__category">{category.subcategoryLabel}</p>
            <p className="mc-show__counter" aria-live="polite">
              <span className="mc-show__counter-now">{pad(index + 1)}</span>
              <span className="mc-show__counter-sep" aria-hidden="true">
                /
              </span>
              <span className="mc-show__counter-all">{pad(n)}</span>
              <span className="mc-show__sr">
                {' '}
                — {cur.kicker ? `${cur.kicker}, ` : ''}
                {cur.name}
              </span>
            </p>
            <div className="mc-show__names">
              {machines.map((x, i) => (
                <div className={`mc-show__name-block${place(i)}`} key={x.machine.id} aria-hidden={i !== index}>
                  {x.kicker && <p className="mc-show__kicker">{x.kicker}</p>}
                  <h3 className="mc-show__name" style={{ '--chars': x.chars } as CSSProperties}>
                    {x.name}
                  </h3>
                  <span className="mc-show__name-rule" aria-hidden="true" />
                  <p className="mc-show__line">{x.story}</p>
                </div>
              ))}
            </div>
            {/* Mirrors the foot on the right: the arrow at the outer edge, the
                tagline beside it, both arrows on one line. */}
            <div className="mc-show__foot mc-show__foot--left">
              <div className="mc-show__step mc-show__step--prev">
                <button
                  className="mc-show__arrow"
                  type="button"
                  aria-label="Previous machine"
                  disabled={index === 0}
                  onClick={() => goTo(index - 1)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M19 12H5M11 6l-6 6 6 6" />
                  </svg>
                </button>
                <span className="mc-show__step-label" aria-hidden="true">
                  Prev
                </span>
              </div>
              <p className="mc-show__tag mc-show__tag--left" aria-hidden="true">
                Powering
                <br />
                progress
                <br />
                together
              </p>
            </div>
          </div>

          {/* ---- centre: the machine ---- */}
          <div className="mc-show__machines">
            {machines.map((x, i) => {
              /* Only the machine in view and the two either side carry an
                 image, so the next ones are already loaded when the reader
                 arrives and the rest of the category costs nothing yet. */
              const near = Math.abs(i - index) <= 2
              /* The machine's isolated hero asset (build-hero-assets.py): the
                 machine alone on transparency, cropped to itself. Never the
                 photograph it came from - no sky, site or studio sweep. */
              const shot = x.machine.hero
              return (
                <button
                  key={x.machine.id}
                  className={`mc-show__slide${place(i)} is-cutout`}
                  type="button"
                  tabIndex={i === index ? 0 : -1}
                  aria-hidden={i !== index}
                  aria-label={`Open ${x.kicker ? `${x.kicker} ` : ''}${x.name}`}
                  onClick={() => onOpenMachine(x.machine.id)}
                >
                  <span className="mc-show__shadow" aria-hidden="true" />
                  {near && shot && (
                    <img
                      className="mc-show__img"
                      src={shot.src}
                      srcSet={shot.srcset}
                      sizes="(max-width: 900px) 92vw, 56vw"
                      alt=""
                      width={shot.w}
                      height={shot.h}
                      /* Never drawn wider than the asset itself: the few
                         machines Hitachi only publishes small would otherwise
                         be stretched soft to fill the stage. */
                      style={{ maxWidth: `min(100%, ${shot.w}px)` }}
                      decoding="async"
                      draggable="false"
                    />
                  )}
                </button>
              )
            })}
            <div className="mc-show__dots" aria-hidden="true">
              {machines.map((x, i) => (
                <span key={x.machine.id} className={`mc-show__dot${i === index ? ' is-on' : ''}`} />
              ))}
            </div>
            <p className={`mc-show__cue${index === n - 1 ? ' is-done' : ''}`} aria-hidden="true">
              <span className="mc-show__mouse" />
              Scroll to explore the range
            </p>
          </div>

          {/* ---- right: what the workbook says about it ---- */}
          <div className="mc-show__facts">
            <span className="mc-show__rule" aria-hidden="true" />
            <div className="mc-show__rows">
              {machines.map((x, i) => (
                <dl className={`mc-show__dl${place(i)}`} key={x.machine.id} aria-hidden={i !== index}>
                  {x.rows.map((r: InfoRow) => (
                    <div className={`mc-show__row mc-show__row--${r.key}`} key={r.key}>
                      <span className="mc-show__row-icon" aria-hidden="true">
                        {ROW_ICONS[r.key]}
                      </span>
                      <dt>{r.label}</dt>
                      <dd>{r.value}</dd>
                    </div>
                  ))}
                </dl>
              ))}
            </div>
            {/* In the flow, under the facts: however many rows a machine has,
                nothing can land on top of the button. */}
            <div className="mc-show__foot">
              <p className="mc-show__tag mc-show__tag--right" aria-hidden="true">
                Reliable
                <br />
                solutions
                <br />
                for a tougher
                <br />
                tomorrow
              </p>
              <div className="mc-show__step mc-show__step--next">
                <button
                  className="mc-show__arrow mc-show__arrow--next"
                  type="button"
                  aria-label="Next machine"
                  disabled={index === n - 1}
                  onClick={() => goTo(index + 1)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
                <span className="mc-show__step-label" aria-hidden="true">
                  Next
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
