import { useRef, useState } from 'react'
import { storyStates, activeStateIndex } from '../../data/storyStates'
import { useProgressEffect } from '../../hooks/progressStore'

/**
 * Chapter position as an architectural measurement line: the current state
 * number over the total, and one thin rule that fills across the whole story.
 * Six stacked numbers would be a menu; this is a scale marking.
 */
export function StoryProgress() {
  const fillRef = useRef(null)
  const [active, setActive] = useState(0)

  useProgressEffect((p) => {
    if (fillRef.current) {
      fillRef.current.style.transform = `scaleY(${p.toFixed(4)})`
    }
    setActive((prev) => {
      const next = activeStateIndex(p)
      return next === prev ? prev : next
    })
  })

  return (
    <div className="measure" aria-hidden="true">
      <span className="measure__current">{String(active + 1).padStart(2, '0')}</span>
      <span className="measure__rule">
        <span className="measure__fill" ref={fillRef} />
      </span>
      <span className="measure__total">
        {String(storyStates.length).padStart(2, '0')}
      </span>
    </div>
  )
}

/** The live chapter name, announced to assistive technology. */
export function ChapterAnnouncer() {
  const [active, setActive] = useState(0)

  useProgressEffect((p) => {
    setActive((prev) => {
      const next = activeStateIndex(p)
      return next === prev ? prev : next
    })
  })

  return (
    <p className="visually-hidden" aria-live="polite">
      {storyStates[active].eyebrow}
    </p>
  )
}
