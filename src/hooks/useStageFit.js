import { useEffect, useState } from 'react'

/**
 * Where the machine's picture actually lands on screen.
 *
 * Three boxes are involved. The **stage** is the pinned viewport, whose pixel
 * coordinates the connection paths are drawn in. The **box** is the inset
 * rectangle reserved for the machine, and carries the camera scale. The
 * **media** element inside it is sized to the clip's own 16:9, so its layout
 * box *is* the picture — no letterbox of its own.
 *
 * Layout offsets are read rather than bounding rects, so the camera scale is
 * excluded here and applied explicitly in anchorToStage. Everything is
 * measured rather than assumed, because the insets are percentages and vh and
 * so change with every viewport.
 */
export function useStageFit(stageRef, boxRef, mediaRef) {
  const [fit, setFit] = useState(null)

  useEffect(() => {
    const stage = stageRef.current
    if (!stage) return undefined

    const measure = () => {
      const box = boxRef.current
      const media = mediaRef.current
      const { width, height } = stage.getBoundingClientRect()
      if (!width || !height || !box || !media || !media.offsetWidth) return

      setFit({
        stageW: width,
        stageH: height,
        // The picture, in stage coordinates, before the camera scale.
        videoX: box.offsetLeft + media.offsetLeft,
        videoY: box.offsetTop + media.offsetTop,
        videoW: media.offsetWidth,
        videoH: media.offsetHeight,
        // The box scales about its own centre.
        originX: box.offsetLeft + box.offsetWidth / 2,
        originY: box.offsetTop + box.offsetHeight / 2,
      })
    }

    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(stage)
    if (mediaRef.current) observer.observe(mediaRef.current)
    window.addEventListener('orientationchange', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('orientationchange', measure)
    }
  }, [stageRef, boxRef, mediaRef])

  return fit
}

/**
 * A point in video-frame space (0..1 of the clip's own frame) → stage pixels,
 * including the camera scale the picture is currently under.
 */
export function anchorToStage(fit, anchor, scale = 1) {
  const x = fit.videoX + anchor.x * fit.videoW
  const y = fit.videoY + anchor.y * fit.videoH
  if (scale === 1) return { x, y }
  return {
    x: fit.originX + (x - fit.originX) * scale,
    y: fit.originY + (y - fit.originY) * scale,
  }
}

/** A point in stage space (0..1 of the pinned viewport) → stage pixels. */
export function cardToStage(fit, card) {
  return { x: card.x * fit.stageW, y: card.y * fit.stageH }
}
