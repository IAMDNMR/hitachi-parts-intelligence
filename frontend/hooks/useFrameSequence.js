import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Loads a numbered frame sequence and draws one frame at a time to a canvas.
 *
 * Sections 01-04 each carried their own copy of this. The four copies were
 * byte-identical in the part that matters — the progressive loader — and
 * differed only in three details, which are the options below. Nothing here
 * changes behaviour; it is the same code, in one place.
 *
 * WHY A CANVAS AND NOT A <video>
 * ------------------------------
 * A video seek is a request, not a guarantee: the decoder may drop it, round
 * it to a nearby keyframe, or still be servicing it when the scroll has moved
 * on. Frame N is simply frame N, in every browser, forwards and backwards
 * alike — which is what makes reverse scrolling land exactly.
 *
 * LOADING
 * -------
 * Frames are fetched in order behind a small request pool, so the first frame
 * paints almost immediately and the rest fill in behind it. A frame that
 * arrives while it is the one being asked for paints on arrival.
 *
 * Until a given frame has loaded, the nearest one that *has* is drawn instead
 * — searching outward from the wanted index — so scrubbing during load is
 * continuous rather than blank.
 *
 * The sequence is considered failed if frame 0 will not load, or if more than
 * half the frames fail. Callers render their own fallback from `failed`.
 *
 * WHAT THIS HOOK DOES NOT DO
 * --------------------------
 * It does not map scroll position to a frame index. Each section maps its own
 * — the Hero runs progress through a story curve, the others map linearly —
 * and those mappings are section content, not loading machinery. Callers own
 * their `useProgressEffect` and call `draw(index)`.
 *
 * @param {object}   opts
 * @param {string[]} opts.urls            frame URLs, already in order
 * @param {object}   opts.canvasRef       ref to the target <canvas>
 * @param {number}   [opts.concurrency=8] frames in flight at once
 * @param {boolean}  [opts.resizeToFrame=true]
 *        true  — size the canvas to each frame's own pixels and clear before
 *                drawing. What Sections 02-04 need: their frames are cut-outs
 *                whose dimensions define the layout box.
 *        false — draw into the canvas at whatever size it already is, without
 *                clearing. What the Hero needs: its canvas is fixed at the
 *                clip's 16:9 so the connection layer can measure it, and its
 *                frames are opaque, so clearing first would only flicker.
 * @param {boolean}  [opts.redrawSameIndex=false]
 *        Whether asking for the frame already on screen repaints it. The Hero
 *        needs true because it derives a backdrop from each draw.
 * @param {(image: HTMLImageElement) => void} [opts.onFrame]
 *        Runs after a frame is drawn, with the image that was drawn. The Hero
 *        uses it to sample the studio's edge tones into its backdrop.
 *
 * @returns {{ draw: (index: number) => void, failed: boolean, count: number }}
 */
export function useFrameSequence({
  urls,
  canvasRef,
  concurrency = 8,
  resizeToFrame = true,
  redrawSameIndex = false,
  onFrame,
}) {
  const count = urls.length
  const imagesRef = useRef([])
  const wantedRef = useRef(0)
  const [failed, setFailed] = useState(false)

  // Kept in a ref so a caller can pass an inline callback without making the
  // loader effect re-run and restart every download.
  const onFrameRef = useRef(onFrame)
  onFrameRef.current = onFrame

  // The one place a frame is actually put on the canvas. Both the scroll
  // path and the load-on-arrival path go through it, so there is no second
  // copy of the resize/clear/draw rules to drift out of step.
  const paint = useCallback(
    (image) => {
      const canvas = canvasRef.current
      if (!canvas) return
      if (resizeToFrame && canvas.width !== image.naturalWidth) {
        canvas.width = image.naturalWidth
        canvas.height = image.naturalHeight
      }
      const ctx = canvas.getContext('2d')
      if (resizeToFrame) ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
      if (onFrameRef.current) onFrameRef.current(image)
    },
    [canvasRef, resizeToFrame],
  )
  const paintRef = useRef(paint)
  paintRef.current = paint

  const draw = useCallback(
    (index) => {
      const canvas = canvasRef.current
      const images = imagesRef.current
      if (!canvas) return
      // Index equality only — deliberately not "…and the frame has loaded".
      // While the sequence is still downloading, the nearest-loaded fallback
      // is already on screen and asking for the same index again would draw
      // the same substitute. Matching the pre-refactor guard exactly.
      if (!redrawSameIndex && index === wantedRef.current) return

      wantedRef.current = index

      let image = images[index]
      if (!image) {
        // Nearest frame that has arrived, so a scrub mid-load never goes blank.
        for (let step = 1; step < count; step += 1) {
          if (images[index - step]) {
            image = images[index - step]
            break
          }
          if (images[index + step]) {
            image = images[index + step]
            break
          }
        }
      }
      if (!image) return

      paint(image)
    },
    [canvasRef, count, redrawSameIndex, paint],
  )

  useEffect(() => {
    if (!count) {
      setFailed(true)
      return undefined
    }

    let cancelled = false
    const images = new Array(count)
    imagesRef.current = images
    let next = 0
    let failures = 0

    const loadNext = () => {
      if (cancelled) return
      const index = next
      next += 1
      if (index >= count) return

      const img = new Image()
      img.decoding = 'async'
      const done = (ok) => {
        if (cancelled) return
        if (ok) {
          images[index] = img
          // Paint it the moment it arrives if it is the frame being asked for.
          if (index === wantedRef.current) paintRef.current(img)
        } else {
          failures += 1
          if (index === 0 || failures > count / 2) setFailed(true)
        }
        loadNext()
      }
      img.onload = () => done(true)
      img.onerror = () => done(false)
      img.src = urls[index]
    }

    for (let k = 0; k < concurrency; k += 1) loadNext()
    return () => {
      cancelled = true
    }
    // `urls` is a module-level constant in every caller, so this runs once.
  }, [urls, count, concurrency])

  return { draw, failed, count }
}
