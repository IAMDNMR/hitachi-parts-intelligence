import { useEffect, useMemo, useRef, useState } from 'react'
import { NODE_TYPE_LABELS } from '../data/graph'
import type { GroundNode } from '../types/ground'

/**
 * FINDING A NODE.
 *
 * Seventy-five nodes across nineteen layers, and until now the only way to
 * reach one was to already know which branch it was down and click your way
 * there. In front of a room that is fatal: someone asks "where does warranty
 * sit?" and the answer is a hunt.
 *
 * Matching is on the label first and the summary second, because the question
 * is nearly always a name — "warranty", "Neovia", "returns" — and matching
 * prose as readily as titles buries the node actually called Warranty under
 * every node that mentions it. A label match always outranks a summary match
 * for the same reason.
 *
 * Choosing a result calls `activate`, which is the same thing clicking a node
 * does: the graph works out the route to it and draws it. Nothing here knows
 * anything about layout or navigation beyond that one call.
 */
interface Props {
  nodes: readonly GroundNode[]
  onPick: (id: string) => void
}

interface Hit {
  node: GroundNode
  /** Lower is better. 0 = the label starts with the query. */
  rank: number
}

const MAX_HITS = 8

function search(nodes: readonly GroundNode[], raw: string): Hit[] {
  const q = raw.trim().toLowerCase()
  if (q.length < 2) return []

  const hits: Hit[] = []
  for (const node of nodes) {
    const label = node.label.toLowerCase()
    if (label.startsWith(q)) hits.push({ node, rank: 0 })
    else if (label.includes(q)) hits.push({ node, rank: 1 })
    else if (node.summary.toLowerCase().includes(q)) hits.push({ node, rank: 2 })
    else if (node.role && node.role.toLowerCase().includes(q)) hits.push({ node, rank: 3 })
  }

  return hits
    .sort((a, b) => a.rank - b.rank || a.node.label.localeCompare(b.node.label))
    .slice(0, MAX_HITS)
}

export function NodeSearch({ nodes, onPick }: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  /** Which result the arrow keys are on. */
  const [cursor, setCursor] = useState(0)
  const box = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)

  const hits = useMemo(() => search(nodes, query), [nodes, query])

  useEffect(() => {
    setCursor(0)
  }, [query])

  /* Shuts on an outside click or Escape — the same rule every other popover
     in this project follows. */
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  /* "/" focuses the search from anywhere on the page, which is what anyone
     driving this in front of an audience will reach for. Ignored while
     something else already has the keyboard, so it cannot swallow a
     character being typed into a field. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return
      const at = document.activeElement
      if (at instanceof HTMLInputElement || at instanceof HTMLTextAreaElement) return
      e.preventDefault()
      input.current?.focus()
      setOpen(true)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const choose = (node: GroundNode) => {
    onPick(node.id)
    setQuery('')
    setOpen(false)
    input.current?.blur()
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setOpen(false)
      input.current?.blur()
      return
    }
    if (!hits.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setCursor((c) => (c + 1) % hits.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setCursor((c) => (c - 1 + hits.length) % hits.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const hit = hits[cursor] ?? hits[0]
      if (hit) choose(hit.node)
    }
  }

  const showList = open && query.trim().length >= 2

  return (
    <div className="gr__search" ref={box}>
      <input
        ref={input}
        type="search"
        className="gr__search-input"
        value={query}
        placeholder="Find a node…"
        aria-label="Find a node on the map"
        aria-expanded={showList}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />

      {showList && (
        <div className="gr__search-pop" role="listbox">
          {hits.length === 0 ? (
            <p className="gr__search-empty">Nothing on the map matches that.</p>
          ) : (
            hits.map((hit, i) => (
              <button
                key={hit.node.id}
                type="button"
                role="option"
                aria-selected={i === cursor}
                className={`gr__search-hit${i === cursor ? ' is-cursor' : ''}`}
                onMouseEnter={() => setCursor(i)}
                onClick={() => choose(hit.node)}
              >
                <span className="gr__search-hit-label">{hit.node.label}</span>
                <span className="gr__search-hit-kind">{NODE_TYPE_LABELS[hit.node.type]}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
