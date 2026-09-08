import { useEffect, useRef } from 'react'
import { CloseIcon } from './Icons'

/**
 * Overview panel for one after-sales domain.
 *
 * This is the interaction seam for the deeper knowledge experience: today it
 * shows the node's summary, later the same `node.id` routes into a full
 * knowledge view. Everything a deeper view needs is already on the node.
 */
export function NodePanel({ node, onClose }) {
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

      <p className="panel__soon">Detailed view in development</p>
    </aside>
  )
}
