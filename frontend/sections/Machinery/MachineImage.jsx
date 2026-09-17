/**
 * One official Hitachi machine photograph.
 *
 * Every image is a real asset downloaded from Hitachi's own sources and recorded
 * in MACHINE_IMAGE_MANIFEST.xlsx. Nothing here invents a path: the `image` object
 * comes from the generated catalogue, which was built from that manifest. A
 * machine with no official image gets a quiet plate — never a stand-in from
 * another machine.
 *
 * Weight is the whole reason this is a component rather than a bare <img>:
 *
 *  - `srcset` + `sizes` let the browser fetch the rendition that fits the slot.
 *    The archive masters are up to 8192 px and 20.6 MB; before this the Machinery
 *    entry view pulled 22.8 MB to fill seven slots ~270 px wide.
 *  - `loading="lazy"` on everything except the one image above the fold, so a
 *    category of eighteen machines costs one screenful, not eighteen.
 *  - intrinsic width/height so the layout does not jump as they arrive.
 */
export function MachineImage({ image, alt, priority = false, sizes, cutout = false, className = '' }) {
  if (!image) {
    return (
      <span
        className={`mi mi--empty ${className}`}
        role="img"
        aria-label={`${alt} — no official image`}
      >
        <span className="mi__empty-mark" aria-hidden="true" />
      </span>
    )
  }

  /* A cut-out is a transparent WebP of the same official photograph with the
     white studio sweep removed. It exists only where Hitachi shot the machine on
     white; on-location frames have none and fall back to the opaque rendition. */
  const use = cutout && image.cut ? image.cut : image

  return (
    <img
      className={`mi ${className}`}
      src={use.src}
      srcSet={use.srcset}
      /* Slots on this section are never full-bleed: a band's machine sits in
         roughly half the content width, a tile in a third of it, and the detail
         hero takes most of it. Without this the browser assumes 100vw and
         over-fetches every time. */
      sizes={sizes || '(max-width: 900px) 90vw, 45vw'}
      alt={alt}
      width={image.w || undefined}
      height={image.h || undefined}
      loading={priority ? 'eager' : 'lazy'}
      /* Decoding off the main thread keeps hover transitions smooth while a
         gallery further down is still arriving. */
      decoding="async"
      /* Lowercase deliberately: React 18 does not know the camelCase
         `fetchPriority` prop — it warns and drops it. Lowercase passes straight
         through to the DOM, which is where the browser reads it. */
      fetchpriority={priority ? 'high' : 'low'}
      draggable="false"
    />
  )
}
