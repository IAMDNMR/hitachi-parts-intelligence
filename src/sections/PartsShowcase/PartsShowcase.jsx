import { useCallback, useMemo, useRef, useState } from 'react'
import './PartsShowcase.css'

import {
  ProgressContext,
  createProgressStore,
  useProgressEffect,
} from '../../hooks/progressStore'
import { useScrollProgress } from '../../hooks/useScrollProgress'
import { useFrameSequence } from '../../hooks/useFrameSequence'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import {
  partsCatalogue,
  partAttributes,
  FRAMES_PER_PART,
} from '../../data/partsCatalogue'
import { PartIcon } from './PartIcons'

/**
 * The parts sequence: EVERY frame of parts-video.mp4 — all 240, none
 * skipped — cut out against its white studio by
 * backend/video-processing/extract_section03.py. They live under
 * assets/source/ with the other extracted source material; Vite resolves
 * them at build time and emits them as hashed assets.
 */
const FRAME_MODULES = import.meta.glob('../../../assets/source/section-03/parts-frames/*.webp', {
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

const TOTAL = partsCatalogue.length
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

/** Scroll progress 0..1 -> frame index, and frame index -> which part. */
const frameAt = (p) => clamp(Math.round(p * (COUNT - 1)), 0, COUNT - 1)

/** Every part owns the same number of frames, so this is a division. */
function partAtFrame(frame) {
  return clamp(Math.floor(frame / FRAMES_PER_PART), 0, TOTAL - 1)
}

export function PartsShowcase() {
  const sectionRef = useRef(null)
  const reducedMotion = useReducedMotion()
  const store = useMemo(() => createProgressStore(), [])

  useScrollProgress({ sectionRef, store, enabled: !reducedMotion })

  /** Scrolls so that the middle of part `index` is on screen. */
  const goToPart = useCallback((index) => {
    const section = sectionRef.current
    if (!section || COUNT < 2) return
    const i = clamp(index, 0, TOTAL - 1)
    const frame = i * FRAMES_PER_PART + (FRAMES_PER_PART - 1) / 2
    const distance = section.offsetHeight - window.innerHeight
    window.scrollTo({
      top: section.offsetTop + distance * (frame / (COUNT - 1)),
      behavior: 'smooth',
    })
  }, [])

  if (reducedMotion) return <StaticParts />

  return (
    <ProgressContext.Provider value={store}>
      <section
        className="parts"
        ref={sectionRef}
        id="parts"
        aria-labelledby="parts-title"
      >
        <div className="parts__viewport">
          <div className="parts__grid">
            <IntroColumn />
            <PartStage />
            <PartPanel onGoToPart={goToPart} />
          </div>

          <PartRail onGoToPart={goToPart} />

          <p className="parts__scroll-hint">
            <PartIcon name="mouse" size={18} />
            <span className="parts__scroll-rule" aria-hidden="true" />
            Scroll to explore parts
          </p>
        </div>

        {/* The whole catalogue as prose, for assistive technology and for
            anyone who never scrolls it. */}
        <PartsTranscript />
      </section>
    </ProgressContext.Provider>
  )
}

/* ------------------------------------------------------------------ left */

function IntroColumn() {
  return (
    <div className="parts__intro">
      <p className="parts__kicker">
        <span className="parts__kicker-num">03</span>
        <span className="parts__kicker-rule" aria-hidden="true" />
        Parts
      </p>

      <h2 className="parts__title" id="parts-title">
        <span>The right</span>
        <span className="parts__title-accent">part.</span>
        <span>When it</span>
        <span className="parts__title-accent">matters.</span>
      </h2>

      <span className="parts__tick" aria-hidden="true" />

      <p className="parts__lede">
        Genuine Hitachi parts, engineered for performance, reliability and a
        precise fit.
      </p>

    </div>
  )
}

/* ---------------------------------------------------------------- centre

   The part, drawn a frame at a time.

   Scroll position picks a frame and the canvas draws it — the same
   mechanism the Hero and Section 02 use. A <video> seek is a request the
   decoder may drop or round to a nearby keyframe; frame N is simply frame N,
   in every browser, forwards and backwards alike.

   Each part has its own crop, so it fills the frame and lands on the page
   as large as the layout allows. Within a part the crop is constant, so it
   sits still while it turns; and because all ten crops share one aspect
   ratio the canvas box keeps its proportions across a cut.
-------------------------------------------------------------------------- */
function PartStage() {
  const canvasRef = useRef(null)
  const { draw, failed } = useFrameSequence({
    urls: FRAME_URLS,
    canvasRef,
    concurrency: CONCURRENCY,
  })

  useProgressEffect((p) => {
    if (!COUNT) return
    draw(frameAt(p))
  })

  return (
    <div className="parts__stage">
      {failed ? (
        <p className="parts__stage-failed">
          The part sequence could not be loaded. Every part is still listed
          alongside.
        </p>
      ) : (
        <canvas
          ref={canvasRef}
          className="parts__canvas"
          // Placeholder ratio only; useFrameSequence resizes to the frames'
          // own pixels as soon as the first one lands.
          width="805"
          height="567"
          // Decorative: the part is named and described in the panel beside
          // it, and in the transcript.
          aria-hidden="true"
        />
      )}
      <p className="parts__view">
        <PartIcon name="orbit" size={18} />
        360° view
      </p>
    </div>
  )
}

/* ----------------------------------------------------------------- right */

function usePartIndex() {
  const [index, setIndex] = useState(0)
  useProgressEffect((p) => {
    const next = partAtFrame(frameAt(p))
    setIndex((prev) => (prev === next ? prev : next))
  })
  return index
}

function PartPanel({ onGoToPart }) {
  const index = usePartIndex()
  const part = partsCatalogue[index]

  return (
    <div className="parts__panel">
      <p className="parts__counter">
        <span className="parts__counter-now">
          {String(index + 1).padStart(2, '0')}
        </span>
        <span className="parts__counter-total">
          / {String(TOTAL).padStart(2, '0')}
        </span>
      </p>

      <div className="parts__detail" key={part.id}>
        <h3 className="parts__name">{part.name}</h3>

        <p className="parts__category">
          <PartIcon name="tag" size={15} />
          {part.category}
        </p>

        <p className="parts__description">{part.description}</p>

        <ul className="parts__attrs">
          {part.attributes.map((key) => {
            const attr = partAttributes[key]
            return (
              <li className="parts__attr" key={key}>
                <PartIcon name={attr.icon} size={14} />
                {attr.label}
              </li>
            )
          })}
        </ul>
      </div>

      <div className="parts__nav">
        <button
          type="button"
          className="parts__nav-button"
          onClick={() => onGoToPart(index - 1)}
          disabled={index === 0}
          aria-label="Previous part"
        >
          <span className="parts__nav-back">
            <PartIcon name="arrow" size={18} />
          </span>
        </button>
        <button
          type="button"
          className="parts__nav-button parts__nav-button--next"
          onClick={() => onGoToPart(index + 1)}
          disabled={index === TOTAL - 1}
          aria-label="Next part"
        >
          <PartIcon name="arrow" size={18} />
        </button>
      </div>
    </div>
  )
}

/** The 01–10 rail on the outer edge. Each number seeks to its part. */
function PartRail({ onGoToPart }) {
  const active = usePartIndex()

  return (
    <nav className="parts__rail" aria-label="Parts">
      <span className="parts__rail-line" aria-hidden="true" />
      <ol>
        {partsCatalogue.map((part, i) => (
          <li key={part.id} className={i === active ? 'is-active' : undefined}>
            <button
              type="button"
              onClick={() => onGoToPart(i)}
              aria-current={i === active ? 'true' : undefined}
            >
              <span className="parts__rail-dot" aria-hidden="true" />
              <span className="parts__rail-num">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className="visually-hidden">{part.name}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function PartsTranscript() {
  return (
    <div className="visually-hidden">
      {partsCatalogue.map((part, i) => (
        <section key={part.id}>
          <h3>{`${String(i + 1).padStart(2, '0')} of ${TOTAL} — ${part.name}`}</h3>
          <p>{part.category}</p>
          <p>{part.description}</p>
          <ul>
            {part.attributes.map((key) => (
              <li key={key}>{partAttributes[key].label}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

/**
 * Reduced motion: the ten parts as a plain list, each with the middle frame
 * of its own segment. Nothing is pinned and nothing scrubs.
 */
function StaticParts() {
  return (
    <section className="parts parts--static" id="parts" aria-labelledby="parts-title">
      <IntroColumn />

      {partsCatalogue.map((part, i) => {
        const url = FRAME_URLS[i * FRAMES_PER_PART + Math.floor(FRAMES_PER_PART / 2)]
        return (
          <article className="parts__static-part" key={part.id}>
            {url && <img src={url} alt={part.name} decoding="async" />}
            <div>
              <p className="parts__counter">
                <span className="parts__counter-now">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="parts__counter-total">
                  / {String(TOTAL).padStart(2, '0')}
                </span>
              </p>
              <h3 className="parts__name">{part.name}</h3>
              <p className="parts__category">
                <PartIcon name="tag" size={15} />
                {part.category}
              </p>
              <p className="parts__description">{part.description}</p>
              <ul className="parts__attrs">
          {part.attributes.map((key) => {
            const attr = partAttributes[key]
            return (
              <li className="parts__attr" key={key}>
                <PartIcon name={attr.icon} size={14} />
                {attr.label}
              </li>
            )
          })}
        </ul>
            </div>
          </article>
        )
      })}
    </section>
  )
}
