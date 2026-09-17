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
import { serviceSteps, serviceNavSteps, serviceSystems } from '../../data/serviceSteps'
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
 * Which frames belong to which service stage (the 5 numbered ones, NOT the
 * field beat). Read from the extractor's own map so the two can never
 * disagree. Ranges in the file are 1-based and inclusive; these are 0-based
 * and inclusive, in process order.
 */
const NAV_STAGE_FRAMES = serviceNavSteps.map((step) => {
  const r = frameMap.stages[step.id]
  return { start: r.start - 1, end: r.end - 1 }
})

/**
 * Field beat: the outdoor frames reused as the opening establishing sequence.
 * Frames 72–84 (0-based) — the first 13 of the 18 outdoor frames, so the
 * opening and the ending (which uses all 18) feel intentionally distinct.
 */
const FIELD_FRAME_START = 72
const FIELD_FRAME_END = 84
const FIELD_FRAME_COUNT = FIELD_FRAME_END - FIELD_FRAME_START + 1

/**
 * The field beat occupies the first 1/7 of the total scroll distance.
 * After this threshold, the numbered service journey (Inspect → Back to Work)
 * takes over. Total section height is 700vh (was 600vh).
 */
const FIELD_PHASE_END = 1 / 7

/** Frame index -> which NAV stage (0-4) is being shown. */
function navStageAtFrame(frame) {
  for (let i = NAV_STAGE_FRAMES.length - 1; i >= 0; i -= 1) {
    if (frame >= NAV_STAGE_FRAMES[i].start) return i
  }
  return 0
}

const CONCURRENCY = 6
const NAV_TOTAL = serviceNavSteps.length
const NAV_LAST = NAV_TOTAL - 1
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

export function ServiceExperience() {
  const sectionRef = useRef(null)
  const reducedMotion = useReducedMotion()
  const store = useMemo(() => createProgressStore(), [])

  useScrollProgress({ sectionRef, store, enabled: !reducedMotion })

  /** Scrolls so that nav stage `index` is the one being read. */
  const goToStep = useCallback((index) => {
    const section = sectionRef.current
    if (!section) return
    const i = clamp(index, 0, NAV_LAST)
    const { start, end } = NAV_STAGE_FRAMES[i]
    const frame = (start + end) / 2
    // Map the desired frame back to a scroll position, accounting for the
    // field phase occupying the first 1/7 of scroll.
    const serviceProgress = frame / (COUNT - 1)
    const overallProgress = FIELD_PHASE_END + serviceProgress * (1 - FIELD_PHASE_END)
    const distance = section.offsetHeight - window.innerHeight
    window.scrollTo({
      top: section.offsetTop + distance * overallProgress,
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
 * Returns the active step index into `serviceSteps` (which includes the
 * field beat at index 0). During the field phase, returns 0 (the field
 * beat). During the service journey, returns 1-5 (mapped from the nav
 * stage index).
 */
function useActiveStep() {
  const [index, setIndex] = useState(0)
  useProgressEffect((p) => {
    if (p <= FIELD_PHASE_END) {
      // In the field phase
      setIndex((prev) => (prev === 0 ? prev : 0))
    } else {
      // In the service journey — remap progress to frame
      const serviceP = (p - FIELD_PHASE_END) / (1 - FIELD_PHASE_END)
      const frame = clamp(Math.round(serviceP * (COUNT - 1)), 0, COUNT - 1)
      const navIdx = navStageAtFrame(frame)
      // +1 because serviceSteps[0] is the field beat
      const next = navIdx + 1
      setIndex((prev) => (prev === next ? prev : next))
    }
  })
  return index
}

/**
 * Returns the active nav stage index (0-4, into serviceNavSteps).
 * Returns -1 during the field phase.
 */
function useActiveNavStep() {
  const stepIdx = useActiveStep()
  return stepIdx === 0 ? -1 : stepIdx - 1
}

/* ------------------------------------------------------------------ left */

function IntroColumn() {
  const stepIdx = useActiveStep()
  const stage = serviceSteps[stepIdx]

  return (
    <div className="svc__intro">
      <p className="svc__kicker">
        <span className="svc__kicker-num">04</span>
        <span className="svc__kicker-rule" aria-hidden="true" />
        Service
      </p>

      <div className="svc__intro-live" key={stage.id}>
        <h2 className="svc__title" id="svc-title">
          {stage.headline.map((line) => (
            <span key={line}>{line}</span>
          ))}
          {stage.headlineAccent && (
            <span className="svc__title-accent">{stage.headlineAccent}</span>
          )}
        </h2>

        {!stage.isFieldBeat && (
          <span className="svc__tick" aria-hidden="true" />
        )}

        <p className="svc__lede">{stage.statement}</p>

        {!stage.isFieldBeat && (
          <p className="svc__stage-count">
            <span className="svc__stage-now">{stage.index}</span>
            <span className="svc__stage-total">
              / {String(NAV_TOTAL).padStart(2, '0')}
            </span>
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * The footage, drawn a frame at a time. During the field phase, the outdoor
 * frames (72-84) are drawn. During the service journey, the indoor/outdoor
 * frames are drawn based on the remapped scroll progress.
 *
 * There is no separate canvas for the field beat — the same canvas draws
 * both phases. During the field phase, the canvas draws the outdoor frames
 * directly. A CSS class `.svc__stage--field` is applied during the field
 * phase to adjust the visual treatment (lighter warm grade for daylight
 * footage).
 */
function MachineStage() {
  const canvasRef = useRef(null)
  const [isField, setIsField] = useState(true)
  const { draw, failed } = useFrameSequence({
    urls: FRAME_URLS,
    canvasRef,
    concurrency: CONCURRENCY,
  })

  useProgressEffect((p) => {
    if (!COUNT) return

    if (p <= FIELD_PHASE_END) {
      // Field phase: scrub outdoor frames 72-84 forward
      const fieldP = p / FIELD_PHASE_END
      const frame = FIELD_FRAME_START + Math.round(fieldP * (FIELD_FRAME_COUNT - 1))
      draw(clamp(frame, FIELD_FRAME_START, FIELD_FRAME_END))
      setIsField(true)
    } else {
      // Service journey: remap and scrub all 90 frames
      const serviceP = (p - FIELD_PHASE_END) / (1 - FIELD_PHASE_END)
      draw(clamp(Math.round(serviceP * (COUNT - 1)), 0, COUNT - 1))
      setIsField(false)
    }
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
    <div className={`svc__stage${isField ? ' svc__stage--field' : ''}`}>
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
  return <SystemsRow stepIndex={useActiveStep()} />
}

/**
 * ConSite and Global e-Service. The names hold; what each is doing changes
 * with the stage, so the line under each comes from the active step.
 */
function SystemsRow({ stepIndex }) {
  const stage = serviceSteps[stepIndex]

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

   Only the five NUMBERED stages appear here. The field beat is a context
   beat, not a navigation item.
-------------------------------------------------------------------------- */
function ServiceJourney({ onGoToStep }) {
  const activeNav = useActiveNavStep()

  return (
    <nav className="svc__journey" aria-label="Service stages">
      <span className="svc__journey-line" aria-hidden="true" />
      <ol>
        {serviceNavSteps.map((step, i) => (
          <li key={step.id} className={i === activeNav ? 'is-active' : undefined}>
            <button
              type="button"
              onClick={() => onGoToStep(i)}
              aria-current={i === activeNav ? 'true' : undefined}
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
      {serviceNavSteps.map((step) => (
        <section key={step.id}>
          <h3>{`${step.index} of ${String(NAV_TOTAL).padStart(2, '0')} \u2014 ${step.title}`}</h3>
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
  // Use the inspect stage (index 1 in serviceSteps) for the static intro
  const stage = serviceSteps[1]
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
        {stage.headlineAccent && (
          <span className="svc__title-accent">{stage.headlineAccent}</span>
        )}
      </h2>
      <span className="svc__tick" aria-hidden="true" />
      <p className="svc__lede">{stage.statement}</p>
    </div>
  )
}

/**
 * Reduced motion: the five stages as a plain list. Nothing is pinned and
 * nothing scrubs. The field beat is represented as a brief intro paragraph
 * before the numbered list.
 */
function StaticService() {
  const fieldStage = serviceSteps[0]
  return (
    <section className="svc svc--static" id="service" aria-labelledby="svc-title">
      <StaticIntro />

      <div className="svc__static-field">
        <p className="svc__static-field-headline">
          {fieldStage.headline.join(' ')}
        </p>
        <p className="svc__static-field-statement">{fieldStage.statement}</p>
      </div>

      <ol className="svc__static-steps">
        {serviceNavSteps.map((step, i) => {
          const { start, end } = NAV_STAGE_FRAMES[i]
          const url = FRAME_URLS[Math.round((start + end) / 2)]
          return (
            <li key={step.id}>
              {url && (
                <img
                  className="svc__static-frame"
                  src={url}
                  alt={`${step.title} \u2014 service stage ${step.index}`}
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

      <SystemsRow stepIndex={1} />
    </section>
  )
}
