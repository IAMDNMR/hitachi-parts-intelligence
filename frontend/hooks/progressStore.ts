import { createContext, useContext, useEffect, useRef } from 'react'

/**
 * Story progress is a continuous 0..1 value that updates on every animation
 * frame while the user scrolls. Putting it in React state would re-render the
 * whole overlay tree ~60 times a second, so it lives in a tiny external store
 * instead: components subscribe and write to their own DOM nodes directly.
 *
 * Discrete values derived from progress (the active chapter, for instance)
 * *are* React state — they change a handful of times across the whole story.
 */
export interface ProgressStore {
  get(): number
  set(next: number): void
  subscribe(fn: (value: number) => void): () => void
}

export function createProgressStore(): ProgressStore {
  let value = 0
  const subscribers = new Set<(value: number) => void>()

  return {
    get: () => value,
    set(next) {
      value = next
      subscribers.forEach((fn) => fn(next))
    },
    subscribe(fn) {
      subscribers.add(fn)
      fn(value)
      return () => subscribers.delete(fn)
    },
  }
}

export const ProgressContext = createContext<ProgressStore | null>(null)

export function useProgressStore(): ProgressStore {
  const store = useContext(ProgressContext)
  if (!store) throw new Error('useProgressStore must be used inside <ProgressContext.Provider>')
  return store
}

/**
 * Runs `callback(progress)` on every progress change. The callback is kept in
 * a ref so it can close over fresh values without re-subscribing.
 */
export function useProgressEffect(callback: (progress: number) => void): void {
  const store = useProgressStore()
  const callbackRef = useRef(callback)
  callbackRef.current = callback

  useEffect(() => store.subscribe((p) => callbackRef.current(p)), [store])
}
