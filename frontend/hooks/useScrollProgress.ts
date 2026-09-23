import { useEffect, type RefObject } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import type { ProgressStore } from './progressStore'

gsap.registerPlugin(ScrollTrigger)

/** How hard the eased position chases the scroll position. 1 = no smoothing. */
const SMOOTHING = 0.14
/** Below this the loop has caught up and can stop until the next scroll. */
const SETTLE = 0.0004

interface UseScrollProgressOptions {
  sectionRef: RefObject<HTMLElement | null>
  store: ProgressStore
  enabled: boolean
}

/**
 * Binds vertical scroll over `sectionRef` to a normalised 0..1 story position.
 *
 * ScrollTrigger reports the raw scroll position; an animation-frame loop eases
 * the published position toward it, so fast flicks and reverse scrolling both
 * read smoothly rather than jumping. The loop parks itself once it has caught
 * up, so a stationary reader costs nothing.
 *
 * This used to drive a <video> element's currentTime as well. It no longer
 * does: the machine is an image sequence, so there is nothing to seek. A seek
 * was only ever a request — it could be dropped while the decoder was busy and
 * left the picture on a stale frame — whereas frame N is simply frame N.
 */
export function useScrollProgress({ sectionRef, store, enabled }: UseScrollProgressOptions): void {
  useEffect(() => {
    const section = sectionRef.current
    if (!section) return undefined

    if (!enabled) {
      // Reduced motion: plain scroll position, no easing.
      const trigger = ScrollTrigger.create({
        trigger: section,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => store.set(self.progress),
      })
      return () => trigger.kill()
    }

    let target = 0
    let current = 0
    let frame = 0
    let running = false

    const tick = () => {
      const delta = target - current
      if (Math.abs(delta) < SETTLE) {
        current = target
        running = false
      } else {
        current += delta * SMOOTHING
        frame = requestAnimationFrame(tick)
      }
      store.set(current)
    }

    const wake = () => {
      if (running) return
      running = true
      frame = requestAnimationFrame(tick)
    }

    const trigger = ScrollTrigger.create({
      trigger: section,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        target = self.progress
        wake()
      },
      onRefresh: (self) => {
        target = self.progress
        current = self.progress
        wake()
      },
    })

    // The section is sized in vh, so its height changes whenever the viewport
    // does — including when a mobile browser's URL bar slides away. Without a
    // re-measure the trigger keeps mapping scroll to the old height and the
    // story runs out of step with the scrollbar.
    const resize = new ResizeObserver(() => ScrollTrigger.refresh())
    resize.observe(section)

    target = trigger.progress
    current = trigger.progress
    wake()

    return () => {
      cancelAnimationFrame(frame)
      running = false
      resize.disconnect()
      trigger.kill()
    }
  }, [sectionRef, store, enabled])
}

/** Scrolls the page so the hero sits at a given story progress value. */
export function scrollToProgress(sectionRef: RefObject<HTMLElement | null>, progress: number): void {
  const section = sectionRef.current
  if (!section) return
  const distance = section.offsetHeight - window.innerHeight
  window.scrollTo({
    top: section.offsetTop + distance * Math.min(Math.max(progress, 0), 1),
    behavior: 'smooth',
  })
}
