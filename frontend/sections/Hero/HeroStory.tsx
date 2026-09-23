import { useRef, type CSSProperties } from 'react'
import { storyStates, stateOpacity, stateProgress, type StoryState } from '../../data/storyStates'
import { MACHINE_ID } from '../../data/machineData'
import { useProgressEffect } from '../../hooks/progressStore'
import { ArrowRight } from './Icons'

interface StateGroup {
  root?: HTMLDivElement | null
  heading?: HTMLElement | null
  label?: HTMLElement | null
  note?: HTMLElement | null
}

/**
 * The typographic layer.
 *
 * Each state places its label, headline and note at its own point in the
 * viewport — see the `layout` blocks in data/storyStates.ts. Those points are
 * measured against the machine's silhouette at that state's own position in
 * the clip, so the type always lands in negative space: the excavator is
 * never obscured, and the composition recomposes from state to state instead
 * of holding one fixed text column.
 *
 * Every state's copy drifts slightly as its own progress runs, so the
 * composition breathes with the scroll instead of snapping between layouts.
 */
export function HeroStory({ onExplore }: { onExplore: () => void }) {
  const refs = useRef<Record<string, StateGroup>>({})

  useProgressEffect((p) => {
    storyStates.forEach((state) => {
      const group = refs.current[state.id]
      if (!group) return

      const opacity = stateOpacity(state, p)
      if (group.root) {
        group.root.style.opacity = opacity.toFixed(3)
        group.root.style.visibility = opacity < 0.01 ? 'hidden' : 'visible'
      }
      if (opacity < 0.01) return

      // -1 at the start of the state, +1 at its end.
      const drift = stateProgress(state, p) * 2 - 1

      if (group.heading) {
        group.heading.style.transform = `translate3d(0, ${(-drift * 22).toFixed(
          1,
        )}px, 0) scale(${(1 + drift * 0.012).toFixed(4)})`
      }
      if (group.label) {
        group.label.style.transform = `translate3d(0, ${(-drift * 10).toFixed(1)}px, 0)`
      }
      if (group.note) {
        group.note.style.transform = `translate3d(0, ${(-drift * 14).toFixed(1)}px, 0)`
      }
    })
  })

  const register = <K extends keyof StateGroup,>(id: string, key: K) => (el: StateGroup[K]) => {
    refs.current[id] = refs.current[id] || {}
    refs.current[id][key] = el
  }

  return (
    <div className="type-layer">
      {storyStates.map((state) => {
        const { label, heading, note } = state.layout
        return (
          <div className="type-state" key={state.id} ref={register(state.id, 'root')}>
            <p
              className="type-label"
              style={place(label)}
              ref={register(state.id, 'label')}
            >
              {state.eyebrow}
            </p>

            <h2
              className="type-heading"
              style={{ ...place(heading), fontSize: `${heading.size}vw` }}
              ref={register(state.id, 'heading')}
            >
              {state.heading.map((line) => (
                <span key={line}>{line}</span>
              ))}
            </h2>

            <div className="type-note" style={place(note)} ref={register(state.id, 'note')}>
              <p className="type-note__text">{state.body}</p>
              {state.cta && (
                <a
                  className="cta"
                  href={state.cta.href}
                  onClick={(event) => {
                    event.preventDefault()
                    onExplore()
                  }}
                >
                  {state.cta.label}
                  <ArrowRight />
                </a>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** A layout entry → absolute placement, measured from whichever edge it names. */
function place(spot: StoryState['layout']['label']): CSSProperties {
  const top = spot.below ? `calc(var(--header-h) + ${spot.y}vh)` : `${spot.y}%`
  return spot.anchor === 'right'
    ? { right: `${100 - spot.x}%`, top, textAlign: 'right' }
    : { left: `${spot.x}%`, top }
}

/**
 * Machine identification for the installed-base chapter.
 *
 * One line, set into negative space. Identification only — see
 * data/machineData.ts for why there is no telemetry here.
 */
export function MachineState() {
  const ref = useRef<HTMLParagraphElement>(null)
  const state = storyStates.find((s) => s.showMachineState)!

  useProgressEffect((p) => {
    const el = ref.current
    if (!el) return
    const opacity = stateOpacity(state, p)
    el.style.opacity = opacity.toFixed(3)
    el.style.visibility = opacity < 0.01 ? 'hidden' : 'visible'
  })

  return (
    <p className="machine-id" ref={ref}>
      <span className="machine-id__label">{MACHINE_ID.label}</span>
      <span className="machine-id__value">{MACHINE_ID.value}</span>
    </p>
  )
}
