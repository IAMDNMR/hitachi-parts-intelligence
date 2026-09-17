import { useCallback, useEffect, useRef, useState } from 'react'

import { LANDCROS } from '../../data/landcros'

/** How long each photograph stays up before the next one fades in. */
const SLIDE_MS = 2000

/* One line-drawn mark per kind of fact, in the same 24px, 1.6-stroke style as
   the Reliable / Productive / Sustainable marks on the stage above. */
const icon = (children) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

const SPEC_ICONS = {
  // a date on a calendar
  event: icon(
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="1.5" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4M8 13.5h2.5M13.5 13.5H16M8 17h2.5" />
    </>,
  ),
  // a bolt, for the powertrain
  power: icon(<path d="M13 2.5 5 13.5h6l-1 8 8-11h-6l1-8z" />),
  // a joystick, for how the machine is operated
  operation: icon(
    <>
      <circle cx="12" cy="6" r="2.6" />
      <path d="M12 8.6v7M6 15.6h12l1.5 4.9h-15z" />
    </>,
  ),
  // a rosette, for an award
  award: icon(
    <>
      <circle cx="12" cy="9" r="5.5" />
      <path d="m8.6 13.3-1.6 8.2 5-2.8 5 2.8-1.6-8.2" />
    </>,
  ),
  // a weight, for the operating class
  weight: icon(
    <>
      <circle cx="12" cy="6" r="2.4" />
      <path d="M7.2 9h9.6l3 11.5H4.2z" />
    </>,
  ),
  // an eye, for all-round view from the cab
  view: icon(
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="3" />
    </>,
  ),
}

/* Readers who ask for reduced motion get a still photograph and the arrows. */
function prefersStill() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

/**
 * LANDCROS — the chapter after the range.
 *
 * Below the collection, never on its floor: the seven categories are what HCME
 * sells in Europe today, and these are two concept machines that are not for
 * sale. So the treatment changes: the catalogue is cut-out machines on warm
 * stone; this is white warmed by orange, photographs and a timeline, and every
 * concept carries "not for sale" on its picture.
 *
 * One concept is shown at a time. Two equal cards side by side made the reader
 * compare two things that are not alternatives; a switcher lets each one have
 * the whole stage, its own gallery and its own facts.
 */
export function LandcrosBand() {
  const concepts = LANDCROS.concepts
  const [active, setActive] = useState(0)
  const [shot, setShot] = useState(0)
  const [held, setHeld] = useState(false)
  const [still] = useState(prefersStill)
  const tabs = useRef([])
  const playing = !held && !still

  const count = concepts[active].gallery.length
  useEffect(() => {
    if (!playing) return undefined
    const t = window.setTimeout(() => setShot((n) => (n + 1) % count), SLIDE_MS)
    return () => window.clearTimeout(t)
  }, [playing, shot, count])

  const step = useCallback((d) => setShot((n) => (n + d + count) % count), [count])

  const select = useCallback((i) => {
    setActive(i)
    setShot(0)
  }, [])

  /* Arrow keys move between the two tabs, as a tablist is expected to. */
  const onTabKey = useCallback(
    (event) => {
      const dir = { ArrowRight: 1, ArrowLeft: -1 }[event.key]
      if (!dir) return
      event.preventDefault()
      const next = (active + dir + concepts.length) % concepts.length
      select(next)
      tabs.current[next]?.focus()
    },
    [active, concepts.length, select],
  )

  const c = concepts[active]
  const now = new Date().toISOString().slice(0, 7)

  return (
    <section className="mc-lx" aria-labelledby="mc-lx-title">
      <div className="mc-lx__ground" aria-hidden="true" />
      {/* A rock face at the right edge, drawn and faint - terrain, suggested,
          behind the facts. Two layers for a little depth. */}
      <svg className="mc-lx__rock" viewBox="0 0 300 600" preserveAspectRatio="none" aria-hidden="true">
        <path
          className="mc-lx__rock-far"
          d="M300 20 282 58 290 96 258 132 270 178 236 214 250 262 214 300 232 348 196 392 214 440 184 488 200 540 176 600H300z"
        />
        <path d="M300 110 276 150 286 190 252 236 266 282 230 330 246 372 212 420 230 470 202 522 214 600H300z" />
      </svg>

      <div className="mc-lx__inner">
        <header className="mc-lx__head">
          <div className="mc-lx__brand">
            <p className="mc-lx__eyebrow">What comes next</p>
            <h3 className="mc-lx__title" id="mc-lx-title">
              LANDCROS
            </h3>
            <p className="mc-lx__tagline">{LANDCROS.tagline}</p>
          </div>
          <div className="mc-lx__intro">
            <p className="mc-lx__rebrand">{LANDCROS.rebrand}</p>
            <p className="mc-lx__lede">
              Two concept machines, shown by HCME in Europe, point to where the range is heading.
              Neither is on sale, and neither is one of the machines above.
            </p>
            <a className="mc-lx__link" href={LANDCROS.rebrandSource} target="_blank" rel="noopener noreferrer">
              Read the announcement<span aria-hidden="true"> ↗</span>
            </a>
          </div>
        </header>

        <div className="mc-lx__tabs" role="tablist" aria-label="LANDCROS concept machines">
          {concepts.map((x, i) => (
            <button
              key={x.id}
              ref={(el) => (tabs.current[i] = el)}
              className={`mc-lx__tab${i === active ? ' is-active' : ''}`}
              type="button"
              role="tab"
              id={`mc-lx-tab-${x.id}`}
              aria-selected={i === active}
              aria-controls="mc-lx-panel"
              tabIndex={i === active ? 0 : -1}
              onClick={() => select(i)}
              onKeyDown={onTabKey}
            >
              <span className="mc-lx__tab-num">{String(i + 1).padStart(2, '0')}</span>
              <span className="mc-lx__tab-text">
                <span className="mc-lx__tab-name">{x.name}</span>
                <span className="mc-lx__tab-kind">{x.kind}</span>
              </span>
            </button>
          ))}
        </div>

        <div
          className="mc-lx__panel"
          id="mc-lx-panel"
          role="tabpanel"
          aria-labelledby={`mc-lx-tab-${c.id}`}
        >
          {/* The photograph runs off the left edge of the page and fades into
              the ground on its right and at its foot, so the machine sits in
              the section rather than in a frame. Hovering, or tabbing to the
              arrows, holds the current picture - the way to stop the
              slideshow that works without a mouse. */}
          <figure
            className="mc-lx__stage"
            onMouseEnter={() => setHeld(true)}
            onMouseLeave={() => setHeld(false)}
            onFocus={() => setHeld(true)}
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget)) setHeld(false)
            }}
          >
            {/* Every photograph of the concept is stacked and only the current
                one is opaque, so a change is a crossfade between two loaded
                pictures. Remounting one <img> per change blanked the frame
                while the next file arrived. */}
            <div className="mc-lx__frames">
              {c.gallery.map((g, i) => (
                <img
                  key={g.src}
                  className={`mc-lx__img${i === shot ? ' is-on' : ''}`}
                  src={g.src}
                  srcSet={g.srcset}
                  sizes="(max-width: 1100px) 100vw, 60vw"
                  alt={i === shot ? g.alt : ''}
                  aria-hidden={i === shot ? undefined : true}
                  width={g.w}
                  height={g.h}
                  loading="lazy"
                  decoding="async"
                />
              ))}
            </div>

            <figcaption className="mc-lx__status">Concept · not for sale</figcaption>

            <div className="mc-lx__progress">
              <span className="mc-lx__count" aria-hidden="true">
                {shot + 1} / {c.gallery.length}
              </span>
              {/* One segment per photograph: the ones already shown are full,
                  the current one fills over its two seconds. */}
              <span className="mc-lx__segments" aria-hidden="true">
                {c.gallery.map((g, i) => (
                  <span
                    key={g.src}
                    className={`mc-lx__segment${i < shot ? ' is-done' : ''}${i === shot ? ' is-now' : ''}`}
                  >
                    {i === shot && (
                      <span
                        key={`${c.id}-${shot}-${playing}`}
                        className={`mc-lx__segment-fill${playing ? ' is-running' : ''}`}
                        style={{ animationDuration: `${SLIDE_MS}ms` }}
                      />
                    )}
                  </span>
                ))}
              </span>
            </div>

            <div className="mc-lx__arrows">
              <button className="mc-lx__arrow" type="button" aria-label="Previous photograph" onClick={() => step(-1)}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M19 12H5M11 6l-6 6 6 6" />
                </svg>
              </button>
              <button
                className="mc-lx__arrow mc-lx__arrow--next"
                type="button"
                aria-label="Next photograph"
                onClick={() => step(1)}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </button>
            </div>
          </figure>

          <div className="mc-lx__info">
            <p className="mc-lx__kind">{c.kind}</p>
            <h4 className="mc-lx__name">{c.name}</h4>
            <p className="mc-lx__lead">{c.lead}</p>
            <span className="mc-lx__rule" aria-hidden="true" />
            <dl className="mc-lx__specs">
              {c.specs.map((s) => (
                <div className="mc-lx__spec" key={s.label}>
                  <span className="mc-lx__spec-icon" aria-hidden="true">
                    {SPEC_ICONS[s.icon]}
                  </span>
                  <dt>{s.label}</dt>
                  <dd>{s.value}</dd>
                </div>
              ))}
            </dl>
            <a className="mc-lx__cta" href={c.source} target="_blank" rel="noopener noreferrer">
              Read about {c.name} on hitachicm.com
              <span className="mc-lx__cta-arrow" aria-hidden="true">
                ↗
              </span>
            </a>
          </div>
        </div>

        <ol className="mc-lx__timeline" aria-label="LANDCROS so far">
          {LANDCROS.timeline.map((t) => (
            <li className={`mc-lx__when${t.date > now ? ' is-ahead' : ''}`} key={t.date}>
              <span className="mc-lx__dot" aria-hidden="true" />
              <a className="mc-lx__when-link" href={t.source} target="_blank" rel="noopener noreferrer">
                <span className="mc-lx__when-date">
                  {t.label}
                  {t.date > now && <span className="mc-lx__when-tag">Upcoming</span>}
                </span>
                <span className="mc-lx__when-text">{t.text}</span>
              </a>
            </li>
          ))}
        </ol>

        <p className="mc-lx__connect">
          <span className="mc-lx__connect-name">{LANDCROS.connect.name}</span>
          <span className="mc-lx__connect-line">{LANDCROS.connect.line}</span>
          <a className="mc-lx__link" href={LANDCROS.connect.href} target="_blank" rel="noopener noreferrer">
            Fleet management<span aria-hidden="true"> ↗</span>
          </a>
        </p>
      </div>
    </section>
  )
}
