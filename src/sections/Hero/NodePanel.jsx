import { useEffect, useRef } from 'react'
import { CloseIcon } from './Icons'

/**
 * Overview panel for one after-sales domain.
 *
 * This was written as the seam for a deeper view that did not exist yet, and
 * it ended with the line "Detailed view in development" — a promise printed
 * on the public page. The deeper view is The Ground, it has been built, and
 * every one of these six domains is a node on it, so the promise is now a
 * door: see `groundId` in data/ecosystemNodes.js.
 */
export function NodePanel({ node, onClose, onOpenGround }) {
  const ref = useRef(null)

  useEffect(() => {
    ref.current?.focus()
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <aside
      className="panel"
      role="dialog"
      aria-modal="false"
      aria-label={`${node.panel.title} overview`}
      tabIndex={-1}
      ref={ref}
    >
      <button
        type="button"
        className="panel__close"
        onClick={onClose}
        aria-label="Close panel"
      >
        <CloseIcon />
      </button>

      <p className="eyebrow">After-sales</p>
      <h3 className="panel__title">{node.panel.title}</h3>
      <p className="panel__lead">{node.panel.lead}</p>

      <ul className="panel__list">
        {node.panel.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>

      {node.groundId && (
        <button
          type="button"
          className="panel__go"
          onClick={() => onOpenGround(node.groundId)}
        >
          See it on the map
          <span aria-hidden="true">→</span>
        </button>
      )}
    </aside>
  )
}
