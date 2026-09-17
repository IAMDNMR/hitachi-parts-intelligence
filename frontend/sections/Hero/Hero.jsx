import { useCallback, useMemo, useRef, useState } from 'react'
import './hero.css'

import {
  ProgressContext,
  createProgressStore,
  useProgressEffect,
} from '../../hooks/progressStore'
import { useScrollProgress, scrollToProgress } from '../../hooks/useScrollProgress'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { ecosystemNodes } from '../../data/ecosystemNodes'
import { ramp } from '../../data/storyStates'

import { SiteHeader } from '../../components/SiteHeader/SiteHeader'
import { MachineSequence } from './MachineSequence'
import { HeroStory, MachineState } from './HeroStory'
import { StoryProgress, ChapterAnnouncer } from './StoryProgress'
import { ConnectionLayer } from './ConnectionLayer'
import { JourneyTimeline } from './JourneyTimeline'
import { NodePanel } from './NodePanel'
import { StaticStory } from './StaticStory'
import { StoryTranscript } from './StoryTranscript'

export function Hero({ onOpenGround }) {
  const sectionRef = useRef(null)
  const stageRef = useRef(null)
  const stageBoxRef = useRef(null)
  const mediaRef = useRef(null)
  const reducedMotion = useReducedMotion()

  // One store per Hero instance; every overlay subscribes to it.
  const store = useMemo(() => createProgressStore(), [])

  const [openNodeId, setOpenNodeId] = useState(null)
  const openNode = ecosystemNodes.find((n) => n.id === openNodeId) ?? null

  useScrollProgress({ sectionRef, store, enabled: !reducedMotion })

  const seek = useCallback(
    (progress) => {
      if (reducedMotion) {
        document
          .getElementById(nearestChapterId(progress))
          ?.scrollIntoView({ behavior: 'auto', block: 'start' })
        return
      }
      scrollToProgress(sectionRef, progress)
    },
    [reducedMotion],
  )

  const explore = useCallback(() => {
    document
      .getElementById('after-sales')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const toggleNode = useCallback((id) => {
    setOpenNodeId((prev) => (prev === id ? null : id))
  }, [])

  return (
    <ProgressContext.Provider value={store}>
      <SiteHeader
        position="fixed"
        onBrandClick={(event) => {
          event.preventDefault()
          seek(0)
        }}
      />

      {reducedMotion ? (
        <main id="top">
          <StaticStory onOpenNode={setOpenNodeId} onExplore={explore} />
          {openNode && (
            <NodePanel
              node={openNode}
              onClose={() => setOpenNodeId(null)}
              onOpenGround={onOpenGround}
            />
          )}
        </main>
      ) : (
        <section className="hero" ref={sectionRef} id="top">
          {/* Four deliberate layers. The typography sits under the machine
              and blends into it; only the interface sits on top. */}
          <div className="hero__viewport" ref={stageRef}>
            {/* 2 — editorial typography */}
            <HeroStory onExplore={explore} />

            {/* 3 — the machine: the frame sequence, drawn to a canvas */}
            <MachineSequence
              mediaRef={mediaRef}
              boxRef={stageBoxRef}
              reducedMotion={reducedMotion}
            />

            {/* 4 — interface: connections, journey, measurements */}
            <div className="ui-layer">
              <ConnectionLayer
                stageRef={stageRef}
                boxRef={stageBoxRef}
                mediaRef={mediaRef}
                openNodeId={openNodeId}
                onOpenNode={toggleNode}
              />
              <MachineState />
              <JourneyTimeline />
              <ScrollHint />
              <StoryProgress />
              {openNode && (
                <NodePanel
              node={openNode}
              onClose={() => setOpenNodeId(null)}
              onOpenGround={onOpenGround}
            />
              )}
            </div>
          </div>

          <ChapterAnnouncer />

          <StoryTranscript />
        </section>
      )}
    </ProgressContext.Provider>
  )
}

/** Fades once the reader has understood that scrolling drives the story. */
function ScrollHint() {
  const ref = useRef(null)

  useProgressEffect((p) => {
    const el = ref.current
    if (!el) return
    const opacity = 1 - ramp(p, 0.008, 0.05)
    el.style.opacity = opacity.toFixed(3)
    el.style.visibility = opacity < 0.01 ? 'hidden' : 'visible'
  })

  return (
    <div className="scroll-hint" ref={ref} aria-hidden="true">
      <span>SCROLL</span>
      <span className="scroll-hint__line" />
      <span className="scroll-hint__arrow">↓</span>
    </div>
  )
}

/**
 * Reduced motion has no scroll timeline, so seeking jumps to a chapter
 * heading instead. The ids are namespaced to match StaticStory: the bare
 * names collide with the section anchors further down the page — Section 05
 * also uses id="uptime".
 */
function nearestChapterId(progress) {
  if (progress >= 0.84) return 'chapter-uptime'
  if (progress >= 0.7) return 'chapter-journey'
  if (progress >= 0.56) return 'chapter-parts-services'
  if (progress >= 0.32) return 'chapter-ecosystem'
  if (progress >= 0.16) return 'chapter-installed-base'
  return 'chapter-machine'
}
