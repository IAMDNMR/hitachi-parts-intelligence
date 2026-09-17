import { useCallback, useMemo, useRef, useState } from 'react'
import './AfterSalesEcosystem.css'

import {
  ProgressContext,
  createProgressStore,
  useProgressEffect,
} from '../../hooks/progressStore'
import { useScrollProgress } from '../../hooks/useScrollProgress'
import { useFrameSequence } from '../../hooks/useFrameSequence'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { afterSalesStates } from '../../data/afterSalesStates'
import { EcoIcon } from './EcosystemIcons'

/**
 * The rotation: every frame of the clip's usable arc, as its own image,
 * ordered by filename. Vite resolves these at build time and emits them as
 * hashed assets, so the list is fixed and cache-busted with the bundle.
 */
const FRAME_MODULES = import.meta.glob('../../assets/source/section-02/rotation/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})
const FRAME_URLS = Object.keys(FRAME_MODULES)
  .sort()
  .map((key) => FRAME_MODULES[key])
const COUNT = FRAME_URLS.length

/** Enough in flight to fill the pipe, few enough that frame 0 is never last. */
const CONCURRENCY = 8

const TOTAL = afterSalesStates.length
const LAST_STATE = TOTAL - 1
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

export function AfterSalesEcosystem() {
  const sectionRef = useRef(null)
  const reducedMotion = useReducedMotion()
  const store = useMemo(() => createProgressStore(), [])

  useScrollProgress({ sectionRef, store, enabled: !reducedMotion })

  /** Scrolls so that state `index` is the one being read. */
  const goToState = useCallback((index) => {
    const section = sectionRef.current
    if (!section) return
    const i = clamp(index, 0, LAST_STATE)
    const distance = section.offsetHeight - window.innerHeight
    window.scrollTo({
      top: section.offsetTop + distance * (i / LAST_STATE),
      behavior: 'smooth',
    })
  }, [])

  if (reducedMotion) return <StaticEcosystem />

  return (
    <ProgressContext.Provider value={store}>
      <section
        className="eco"
        ref={sectionRef}
        id="after-sales"
        aria-labelledby="eco-title"
        style={{ '--eco-states': TOTAL }}
      >
        <div className="eco__viewport">
          <div className="eco__grid">
            <div className="eco__col">
              <Masthead />
              <StateCopy />
            </div>
            <MachineRotation />
          </div>

          <StateRail onGoToState={goToState} />
        </div>

        {/* The full section as prose, for assistive technology and for
            anyone who never scrolls it. */}
        <EcosystemTranscript />
      </section>
    </ProgressContext.Provider>
  )
}

function Masthead() {
  return (
    <header className="eco__masthead">
      <p className="eco__kicker">
        <span className="eco__kicker-num">02</span>
        <span className="eco__kicker-rule" aria-hidden="true" />
        After-Sales Ecosystem
      </p>

      <h2 className="eco__title" id="eco-title">
        <span className="eco__title-a">Beyond</span>
        <span className="eco__title-b">the sale.</span>
      </h2>
    </header>
  )
}

/* -------------------------------------------------------------------------
   The machine, drawn a frame at a time.

   Scroll position picks a frame and the canvas draws it. That is the whole
   mechanism, and it is the same one the Hero uses: a <video> seek is a
   request the decoder may drop or round to a nearby keyframe, whereas frame
   N is simply frame N, in every browser.

   Frames arrive in order behind a small request pool, so the first one
   paints almost immediately and the rest fill in; until a given frame has
   arrived the nearest loaded one is drawn, so scrubbing during loading is
   continuous rather than blank.

   Every frame was cut with the same crop, so the machine is planted and only
   its rotation changes. Nothing here transforms the picture.
------------------------------------------------------------------------- */
function MachineRotation() {
  const canvasRef = useRef(null)
  const { draw, failed } = useFrameSequence({
    urls: FRAME_URLS,
    canvasRef,
    concurrency: CONCURRENCY,
  })
  const active = useActiveState()

  useProgressEffect((p) => {
    if (!COUNT) return
    draw(clamp(Math.round(p * (COUNT - 1)), 0, COUNT - 1))
  })

  if (failed) {
    return (
      <div className="eco__machine eco__machine--failed">
        <p>
          The machine sequence could not be loaded. The story alongside still
          describes the full after-sales journey.
        </p>
      </div>
    )
  }

  const state = afterSalesStates[active]

  return (
    <div className="eco__machine">
      <div className="eco__frame-box">
        <canvas
          ref={canvasRef}
          className="eco__canvas"
          width="938"
          height="652"
          // Decorative: the same information is carried by the state copy and
          // the transcript, which screen readers get in document order.
          aria-hidden="true"
        />

        {/* The UI layer on the machine: one marker for the state being read,
            naming it where it belongs rather than inventing a readout. */}
        <span
          className="eco__marker"
          style={{ left: `${state.marker.x * 100}%`, top: `${state.marker.y * 100}%` }}
          aria-hidden="true"
        >
          <span className="eco__marker-dot" />
          <span className="eco__marker-leader" />
          <span className="eco__marker-label" key={state.id}>
            <EcoIcon name={state.icon} size={13} />
            {state.title}
          </span>
        </span>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------
   State copy

   The active state is one of four values, so unlike the frame index it *is*
   React state: it changes four times across the whole section, not sixty
   times a second.
------------------------------------------------------------------------- */
function useActiveState() {
  const [active, setActive] = useState(0)
  useProgressEffect((p) => {
    const next = clamp(Math.round(p * LAST_STATE), 0, LAST_STATE)
    setActive((prev) => (prev === next ? prev : next))
  })
  return active
}

function StateCopy() {
  const active = useActiveState()
  const state = afterSalesStates[active]

  return (
    <div className="eco__state-wrap">
      <p className="eco__counter">
        <span className="eco__counter-now">{state.index}</span>
        <span className="eco__counter-total">
          / {String(TOTAL).padStart(2, '0')}
        </span>
      </p>

      {/* Keying on the state id remounts the block, so the entrance runs on
          every change rather than only on the first. */}
      <article className="eco__state" key={state.id}>
        <p className="eco__state-head">
          <EcoIcon name={state.icon} size={16} />
          <span className="eco__state-title">{state.title}</span>
        </p>

        <h3 className="eco__statement">{state.statement}</h3>
        <p className="eco__line">{state.line}</p>
      </article>
    </div>
  )
}

/** The 01–04 progress indicator. Understated; each number seeks to its state. */
function StateRail({ onGoToState }) {
  const active = useActiveState()

  return (
    <nav className="eco__rail" aria-label="Ecosystem states">
      <span className="eco__rail-line" aria-hidden="true" />
      <ol>
        {afterSalesStates.map((state, i) => (
          <li key={state.id} className={i === active ? 'is-active' : undefined}>
            <button
              type="button"
              onClick={() => onGoToState(i)}
              aria-current={i === active ? 'true' : undefined}
            >
              <span className="eco__rail-tick" aria-hidden="true" />
              <span className="eco__rail-num">{state.index}</span>
              <span className="visually-hidden">{state.title}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function EcosystemTranscript() {
  return (
    <div className="visually-hidden">
      {afterSalesStates.map((state) => (
        <section key={state.id}>
          <h3>{`${state.index} of ${String(TOTAL).padStart(2, '0')} — ${state.title}`}</h3>
          <p>{state.statement}</p>
          <p>{state.line}</p>
        </section>
      ))}
    </div>
  )
}

/**
 * Reduced motion: the same four states, stacked and read at the reader's own
 * pace. Nothing is pinned and nothing scrubs, so each state shows the single
 * frame of the rotation it is keyed to.
 */
function StaticEcosystem() {
  return (
    <section className="eco eco--static" id="after-sales" aria-labelledby="eco-title">
      <Masthead />

      {afterSalesStates.map((state) => (
        <article className="eco__static-state" key={state.id}>
          <div className="eco__state-wrap">
            <p className="eco__counter">
              <span className="eco__counter-now">{state.index}</span>
              <span className="eco__counter-total">
                / {String(TOTAL).padStart(2, '0')}
              </span>
            </p>
            <div className="eco__state">
              <p className="eco__state-head">
                <EcoIcon name={state.icon} size={16} />
                <span className="eco__state-title">{state.title}</span>
              </p>
              <h3 className="eco__statement">{state.statement}</h3>
              <p className="eco__line">{state.line}</p>
            </div>
          </div>

          {FRAME_URLS[state.frame] && (
            <img
              className="eco__static-frame"
              src={FRAME_URLS[state.frame]}
              alt={`Hitachi hydraulic excavator — ${state.title.toLowerCase()}`}
              decoding="async"
            />
          )}
        </article>
      ))}
    </section>
  )
}
