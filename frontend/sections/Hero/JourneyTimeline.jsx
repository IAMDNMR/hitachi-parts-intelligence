import { useRef } from 'react'
import { journeySteps } from '../../data/journey'
import { ramp, stateOpacity, storyStates } from '../../data/storyStates'
import { useProgressEffect } from '../../hooks/progressStore'

const JOURNEY_STATE = storyStates.find((s) => s.showJourney)
/** The signal travels across this progress window. */
const SIGNAL = [0.73, 0.85]

/**
 * From issue to uptime: an orange signal travelling one route.
 *
 * The signal position is a single value; the rail fill, the active step and
 * the trailing states all read from it, so the whole timeline moves as one
 * thing rather than nine independently animated pieces.
 */
export function JourneyTimeline() {
  const rootRef = useRef(null)
  const fillRef = useRef(null)
  const pulseRef = useRef(null)
  const stepRefs = useRef([])

  useProgressEffect((p) => {
    const root = rootRef.current
    if (!root) return

    const opacity = stateOpacity(JOURNEY_STATE, p)
    root.style.opacity = opacity.toFixed(3)
    root.style.visibility = opacity < 0.01 ? 'hidden' : 'visible'
    if (opacity < 0.01) return

    const travelled = ramp(p, SIGNAL[0], SIGNAL[1])

    if (fillRef.current) {
      fillRef.current.style.transform = `scaleX(${travelled.toFixed(4)})`
    }
    if (pulseRef.current) {
      pulseRef.current.style.left = `${(travelled * 100).toFixed(2)}%`
      pulseRef.current.style.opacity = travelled > 0.001 && travelled < 0.999 ? '1' : '0'
    }

    // Steps are evenly spaced along the rail, so the signal reaches step i at
    // i / (n - 1).
    const reachedIndex = travelled * (journeySteps.length - 1)
    journeySteps.forEach((_, i) => {
      const step = stepRefs.current[i]
      if (!step) return
      const reached = reachedIndex >= i - 0.02
      step.dataset.reached = reached ? 'true' : 'false'
      step.dataset.active = Math.abs(reachedIndex - i) < 0.5 ? 'true' : 'false'
    })
  })

  return (
    <div className="journey" ref={rootRef}>
      <div className="journey__rail">
        <span className="journey__fill" ref={fillRef} />
        <span className="journey__pulse" ref={pulseRef} />
      </div>

      <ol className="journey__steps">
        {journeySteps.map((step, i) => (
          <li
            className="journey__step"
            key={step.id}
            data-terminal={step.terminal ? 'true' : undefined}
            ref={(el) => {
              stepRefs.current[i] = el
            }}
          >
            <span className="journey__marker" />
            <span className="journey__label">{step.label}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
