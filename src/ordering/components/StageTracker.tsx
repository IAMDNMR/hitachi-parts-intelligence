import { STAGE_LABELS, STAGE_SEQUENCE } from '../types'
import type { Stage, StatusEvent } from '../types'

interface Props {
  stage: Stage
  events: StatusEvent[]
}

/**
 * The same seven stages The Ground draws as nodes, in the same order, under
 * the same names — so a reader who has looked at the graph recognises this
 * immediately as the same process, not a second vocabulary to learn.
 */
export function StageTracker({ stage, events }: Props) {
  const currentIndex = STAGE_SEQUENCE.indexOf(stage)
  const eventFor = (s: Stage) => events.find((e) => e.stage === s)

  return (
    <ol className="ord__tracker">
      {STAGE_SEQUENCE.map((s, i) => {
        const done = i < currentIndex
        const current = i === currentIndex
        const ev = eventFor(s)
        return (
          <li
            key={s}
            className={`ord__tracker-step${done ? ' is-done' : ''}${current ? ' is-current' : ''}`}
          >
            <span className="ord__tracker-dot" aria-hidden="true" />
            <div className="ord__tracker-body">
              <span className="ord__tracker-label">{STAGE_LABELS[s]}</span>
              {ev && (
                <span className="ord__tracker-meta">
                  {new Date(ev.at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                  {ev.note ? ` — ${ev.note}` : ''}
                </span>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
