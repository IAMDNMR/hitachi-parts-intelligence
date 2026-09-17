import { useCallback, useMemo, useRef, useState } from 'react'
import './ServiceExperience.css'

import {
  ProgressContext,
  createProgressStore,
  useProgressEffect,
} from '../../hooks/progressStore'
import { useScrollProgress } from '../../hooks/useScrollProgress'
import { useFrameSequence } from '../../hooks/useFrameSequence'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { serviceSteps, serviceSystems } from '../../data/serviceSteps'
import { ServiceIcon } from './ServiceIcons'
import frameMap from '../../assets/source/section-04/service-frame-map.json'

/**
 * The service footage: 90 frames cut out of section-4.mp4 by
 * backend/video-processing/select_section04.py — 18 per stage, chosen at
 * equal intervals of motion rather than of time, with the three
 * cross-dissolves excluded.
 *
 * Unlike the earlier sections these are whole photographs, not cut-out
 * subjects: the workshop and the site are part of the picture. So the
 * section shows them as a plate rather than compositing them onto the page.
 */
const FRAME_MODULES = import.meta.glob('../../assets/source/section-04/service-frames/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})
const FRAME_URLS = Object.keys(FRAME_MODULES)
  .sort()
  .map((key) => FRAME_MODULES[key])
const COUNT = FRAME_URLS.length

/**
 * Which frames belong to which stage, read from the extractor's own map so
 * the two can never disagree. Ranges in the file are 1-based and inclusive;
 * these are 0-based and inclusive, in process order.
 */
const STAGE_FRAMES = serviceSteps.map((step) => {
  const r = frameMap.stages[step.id]
  return { start: r.start - 1, end: r.end - 1 }
})

/** Frame index -> which stage is being shown. */
function stageAtFrame(frame) {
  for (let i = STAGE_FRAMES.length - 1; i >= 0; i -= 1) {
    if (frame >= STAGE_FRAMES[i].start) return i
  }
  return 0
}

const CONCURRENCY = 6
const TOTAL = serviceSteps.length
const LAST = TOTAL - 1
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

export function ServiceExperience() {
  const sectionRef = useRef(null)
  const reducedMotion = useReducedMotion()
  const store = useMemo(() => createProgressStore(), [])

  useScrollProgress({ sectionRef, store, enabled: !reducedMotion })

  /** Scrolls so that stage `index` is the one being read. */
  const goToStep = useCallback((index) => {
    const section = sectionRef.current
    if (!section) return
    const i = clamp(index, 0, LAST)
    const { start, end } = STAGE_FRAMES[i]
    const frame = (start + end) / 2
    const distance = section.offsetHeight - window.innerHeight
    window.scrollTo({
      top: section.offsetTop + distance * (frame / (COUNT - 1)),
      behavior: 'smooth',
    })
  }, [])

  if (reducedMotion) return <StaticService />

  return (
    <ProgressContext.Provider value={store}>
      <section
        className="svc"
        ref={sectionRef}
        id="service"
        aria-labelledby="svc-title"
      >
        <div className="svc__viewport">
          <div className="svc__grid">
            <IntroColumn />

            <div className="svc__centre">
              <MachineStage />
              <LiveSystemsRow />
            </div>

            <ServiceJourney onGoToStep={goToStep} />
          </div>

          <p className="svc__scroll-hint">
            <ServiceIcon name="mouse" size={18} />
            <span className="svc__scroll-rule" aria-hidden="true" />
            Scroll to explore service
          </p>
        </div>

        <ServiceTranscript />
      </section>
    </ProgressContext.Provider>
  )
}

/* ---------------------------------------------------------------- shared */

/**
 * Which stage is being read, derived from the frame on screen rather than
 * from the raw scroll fraction — so the copy changes exactly on the cut
 * between one stage's footage and the next.
 *
 * It is a handful of discrete values, so unlike the frame index it *is*
 * React state: it changes five times across the whole section, not sixty
 * times a second.
 */
function useActiveStep() {
  const [index, setIndex] = useState(0)
  useProgressEffect((p) => {
    const frame = clamp(Math.round(p * (COUNT - 1)), 0, COUNT - 1)
    const next = stageAtFrame(frame)
    setIndex((prev) => (prev === next ? prev : next))
  })
  return index
}

/* ------------------------------------------------------------------ left */

function IntroColumn() {
  const stage = serviceSteps[useActiveStep()]

  return (
    <div className="svc__intro">
      <p className="svc__kicker">
        <span className="svc__kicker-num">04</span>
        <span className="svc__kicker-rule" aria-hidden="true" />
        Service
      </p>

      {/* Keyed on the stage, so the whole column re-enters on every change
          rather than only the line at the bottom. */}
      <div className="svc__intro-live" key={stage.id}>
        <h2 className="svc__title" id="svc-title">
          {stage.headline.map((line) => (
            <span key={line}>{line}</span>
          ))}
          <span className="svc__title-accent">{stage.headlineAccent}</span>
        </h2>

        <span className="svc__tick" aria-hidden="true" />

        <p className="svc__lede">{stage.statement}</p>

        <p className="svc__stage-count">
          <span className="svc__stage-now">{stage.index}</span>
          <span className="svc__stage-total">
            / {String(TOTAL).padStart(2, '0')}
          </span>
        </p>
      </div>
    </div>
  )
}

/**
 * The footage, drawn a frame at a time. Same scrubbing mechanism as the
 * earlier sections: scroll picks a frame and the canvas draws it, so
 * forwards and backwards both land exactly.
 *
 * There are no markers over the picture any more. They used to be fractions
 * of a cut-out machine's own box, which worked while the machine was the
 * only thing in the frame; here the camera changes scene and the machine
 * moves through the shot, so a fixed fraction would point at nothing.
 */
function MachineStage() {
  const canvasRef = useRef(null)
  const { draw, failed } = useFrameSequence({
    urls: FRAME_URLS,
    canvasRef,
    concurrency: CONCURRENCY,
  })

  useProgressEffect((p) => {
    if (!COUNT) return
    draw(clamp(Math.round(p * (COUNT - 1)), 0, COUNT - 1))
  })

  if (failed) {
    return (
      <div className="svc__stage svc__stage--failed">
        <p>
          The machine sequence could not be loaded. Every service stage is
          still described alongside.
        </p>
      </div>
    )
  }

  return (
    <div className="svc__stage">
      <ServiceAmbient />
      <div className="svc__machine">
        <canvas
          ref={canvasRef}
          className="svc__canvas"
          width="1280"
          height="720"
          aria-hidden="true"
        />
      </div>
    </div>
  )
}

/**
 * The ambient layer behind the footage.
 *
 * Three concentric arcs and one orange accent, all at very low opacity —
 * enough to give the machine a horizon to sit against as the studio fades
 * out, and nothing more. It is geometry, not decoration: no glow, no
 * gradient fills, no second colour.
 */
function ServiceAmbient() {
  return (
    <svg
      className="svc__ambient"
      viewBox="0 0 1000 620"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* One thin ring the machine sits inside, open at the foot so it reads
          as a drawn mark rather than a container. */}
      <circle
        cx="520"
        cy="300"
        r="292"
        stroke="rgba(214,138,58,0.45)"
        strokeWidth="1.1"
      />
      <circle cx="520" cy="8" r="3" fill="rgba(214,138,58,0.6)" />
    </svg>
  )
}

/** Wraps SystemsRow so the hook runs inside the progress provider. */
function LiveSystemsRow() {
  return <SystemsRow stageIndex={useActiveStep()} />
}

/**
 * ConSite and Global e-Service. The names hold; what each is doing changes
 * with the stage, so the line under each comes from the active step.
 */
function SystemsRow({ stageIndex }) {
  const stage = serviceSteps[stageIndex]

  return (
    <ul className="svc__systems">
      {serviceSystems.map((s) => (
        <li key={s.id}>
          <span className="svc__system-badge">
            <ServiceIcon name={s.icon} size={20} />
          </span>
          <span className="svc__system-copy">
            <span className="svc__system-name">{s.name}</span>
            <span className="svc__system-line" key={stage.id}>
              {stage.systems[s.key]}
            </span>
          </span>
        </li>
      ))}
    </ul>
  )
}

/* -----------------------------------------------------------------  right

   The service journey. One continuous process, not five cards: a single
   hairline runs the height of the column, every stage is a number and a name
   on it, and only the stage being read opens to show its line. The rail and
   the detail panel used to be two separate elements saying the same thing —
   this is both.
-------------------------------------------------------------------------- */
function ServiceJourney({ onGoToStep }) {
  const active = useActiveStep()

  return (
    <nav className="svc__journey" aria-label="Service stages">
      <span className="svc__journey-line" aria-hidden="true" />
      <ol>
        {serviceSteps.map((step, i) => (
          <li key={step.id} className={i === active ? 'is-active' : undefined}>
            <button
              type="button"
              onClick={() => onGoToStep(i)}
              aria-current={i === active ? 'true' : undefined}
            >
              <span className="svc__journey-node" aria-hidden="true" />
              <span className="svc__journey-copy">
                <span className="svc__journey-index">{step.index}</span>
                <span className="svc__journey-name">{step.title}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function ServiceTranscript() {
  return (
    <div className="visually-hidden">
      {serviceSteps.map((step) => (
        <section key={step.id}>
          <h3>{`${step.index} of ${String(TOTAL).padStart(2, '0')} — ${step.title}`}</h3>
          <p>{step.statement}</p>
        </section>
      ))}
      {serviceSystems.map((s) => (
        <section key={s.id}>
          <h3>{s.name}</h3>
          <p>{s.line}</p>
        </section>
      ))}
    </div>
  )
}

/** The masthead without the scroll: stage 01 carries the section's thesis. */
function StaticIntro() {
  const stage = serviceSteps[0]
  return (
    <div className="svc__intro">
      <p className="svc__kicker">
        <span className="svc__kicker-num">04</span>
        <span className="svc__kicker-rule" aria-hidden="true" />
        Service
      </p>
      <h2 className="svc__title" id="svc-title">
        {stage.headline.map((line) => (
          <span key={line}>{line}</span>
        ))}
        <span className="svc__title-accent">{stage.headlineAccent}</span>
      </h2>
      <span className="svc__tick" aria-hidden="true" />
      <p className="svc__lede">{stage.statement}</p>
    </div>
  )
}

/**
 * Reduced motion: the five stages as a plain list. Nothing is pinned and
 * nothing scrubs.
 */
function StaticService() {
  return (
    <section className="svc svc--static" id="service" aria-labelledby="svc-title">
      <StaticIntro />

      <ol className="svc__static-steps">
        {serviceSteps.map((step, i) => {
          const { start, end } = STAGE_FRAMES[i]
          const url = FRAME_URLS[Math.round((start + end) / 2)]
          return (
            <li key={step.id}>
              {url && (
                <img
                  className="svc__static-frame"
                  src={url}
                  alt={`${step.title} — service stage ${step.index}`}
                  decoding="async"
                />
              )}
              <span className="svc__static-copy">
                <span className="svc__journey-index">{step.index}</span>
                <span className="svc__journey-name">{step.title}</span>
                <span className="svc__stage-statement">{step.statement}</span>
              </span>
            </li>
          )
        })}
      </ol>

      <SystemsRow stageIndex={0} />
    </section>
  )
}
