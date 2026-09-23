import { useEffect, useState } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

/** Tracks the user's reduced-motion preference, including live changes. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(QUERY).matches
      : false,
  )

  useEffect(() => {
    if (!window.matchMedia) return undefined
    const mq = window.matchMedia(QUERY)
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return reduced
}
