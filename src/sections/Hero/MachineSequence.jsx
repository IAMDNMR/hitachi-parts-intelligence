import { useCallback, useRef } from 'react'
import { useProgressEffect } from '../../hooks/progressStore'
import { useFrameSequence } from '../../hooks/useFrameSequence'
import { stageScale, progressToClipPosition, clamp } from '../../data/storyStates'

/**
 * Every frame of the clip, as its own image, ordered by filename.
 *
 * The sequence is the exploded-view animation selected out of
 * assets/source/section-01/section-1.mp4 by
 * backend/video-processing/select_section01.py:
 * 90 frames of 192, sampled at equal intervals of motion so the animation's
 * dead hold costs nothing and its fast passages stay smooth. They are
 * written at this canvas's own 1280x720 in RGB, i.e. exactly the format this
 * component already drew, so nothing else here changes.
 *
 * Vite resolves these at build time and emits them as hashed assets, so the
 * list is fixed and the URLs are cache-busted with the rest of the bundle.
 */
const FRAME_MODULES = import.meta.glob('../../../assets/source/section-01/hero-frames/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})
const FRAME_URLS = Object.keys(FRAME_MODULES)
  .sort()
  .map((key) => FRAME_MODULES[key])
const COUNT = FRAME_URLS.length

/** How many frames to fetch at once. Enough to fill the pipe, few enough
    that frame 0 is never stuck behind the other 89. */
const CONCURRENCY = 8

/**
 * The machine, drawn a frame at a time.
 *
 * The scroll position picks a frame and the canvas draws it. That is the whole
 * mechanism, and it is deliberately duller than the <video> it replaces: a
 * video seek is a request the decoder may drop, round to a nearby keyframe, or
 * still be servicing when the scroll has moved on. Frame N is simply frame N,
 * in every browser.
 *
 * Frames arrive in order behind a small request pool, so the first frame paints
 * almost immediately and the rest fill in. Until a given frame has arrived the
 * nearest loaded one is drawn, so scrubbing during loading is continuous rather
 * than blank.
 *
 * The canvas is sized to the clip's own 16:9, so its layout box *is* the
 * picture — which is what lets the connection layer measure components against
 * it. The camera scale is applied to the wrapper, not the canvas, so this box
 * stays transform-free and measurable.
 */
export function MachineSequence({ boxRef, mediaRef, reducedMotion }) {
  const canvasRef = useRef(null)
  const backdropRef = useRef(null)

  const setRefs = useCallback(
    (el) => {
      canvasRef.current = el
      if (mediaRef) mediaRef.current = el
    },
    [mediaRef],
  )

  /**
   * The room around the picture, sampled from the picture's own edges.
   *
   * Drawing the whole frame here and blurring it does not work: the blur
   * drags the machine's orange out into the margins, which is worse than the
   * hard edge it was meant to cure. Four corners alone is too coarse in the
   * other direction -- the room's light varies along each edge, so the margin
   * drifts away from the picture between them.
   *
   * So the top and bottom strips are sampled across their full width. Those
   * two bands are the only part of the frame that is empty room in *every*
   * state: the machine's bounding box over the whole clip spans y 0.03..0.86,
   * so nothing ever reaches them, while its left and right edges do. Each
   * cell averages one box down to a pixel, and the strip becomes a smooth
   * gradient once stretched across the viewport.
   */
  const sampleBackdrop = useCallback((image) => {
    const backdrop = backdropRef.current
    if (!backdrop) return
    const bctx = backdrop.getContext('2d')
    const iw = image.naturalWidth || image.width
    const ih = image.naturalHeight || image.height
    const cols = backdrop.width
    const band = Math.max(2, Math.round(ih * 0.02))
    const step = iw / cols
    for (let c = 0; c < cols; c += 1) {
      const sx = Math.round(c * step)
      const sw = Math.max(1, Math.round(step))
      bctx.drawImage(image, sx, 0, sw, band, c, 0, 1, 1)
      bctx.drawImage(image, sx, ih - band, sw, band, c, 1, 1, 1)
    }
  }, [])

  const { draw, failed } = useFrameSequence({
    urls: FRAME_URLS,
    canvasRef,
    concurrency: CONCURRENCY,
    // The Hero's canvas is fixed at the clip's own 16:9 so the connection
    // layer can measure it, and the frames are opaque, so it is neither
    // resized per frame nor cleared first.
    resizeToFrame: false,
    // Every progress tick repaints, because the backdrop is derived from the
    // frame that was drawn.
    redrawSameIndex: true,
    onFrame: sampleBackdrop,
  })

  useProgressEffect((p) => {
    const box = boxRef.current
    if (box && !reducedMotion) {
      box.style.transform = `scale(${stageScale(p).toFixed(4)})`
    }
    if (!COUNT) return
    const index = clamp(
      Math.round(progressToClipPosition(p) * (COUNT - 1)),
      0,
      COUNT - 1,
    )
    draw(index)
  })

  return (
    <>
      {!failed && (
        <canvas
          className="stage__backdrop"
          ref={backdropRef}
          width="24"
          height="2"
          aria-hidden="true"
        />
      )}
      <div className="stage" ref={boxRef}>
      {failed ? (
        <div className="stage__fallback">
          <p>
            The animated sequence could not be loaded. The story alongside
            still describes the full after-sales journey.
          </p>
        </div>
      ) : (
        <canvas
          ref={setRefs}
          className="stage__media"
          width="1280"
          height="720"
          // Decorative: the same information is carried by the overlay copy
          // and the transcript, which screen readers get in document order.
          aria-hidden="true"
        />
        )}
      </div>
    </>
  )
}
