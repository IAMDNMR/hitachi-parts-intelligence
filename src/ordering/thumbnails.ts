import { FRAMES_PER_PART, partsCatalogue } from '../data/partsCatalogue'

/**
 * A photograph of each part, for the catalogue and the requirement rows.
 *
 * Not stock imagery: these are frames of the project's own parts-video.mp4,
 * already extracted and cut out against their studio white for the Parts
 * Showcase section on the home page. Part i owns frames
 * [i * FRAMES_PER_PART, i * FRAMES_PER_PART + FRAMES_PER_PART - 1], so the
 * middle frame of each part's own run is the one that shows it squarest to
 * camera — the first and last of a run are mid-transition to the next part.
 *
 * The backend does not serve images and should not: it holds the record of
 * a part, not its portrait. The mapping is by catalogue position, which is
 * the same order the video shows them in and the same order the backend
 * seeds them from (backend/parts_ordering/app/seed.py).
 */
const FRAME_MODULES = import.meta.glob(
  '../../assets/source/section-03/parts-frames/*.webp',
  { eager: true, query: '?url', import: 'default' },
)

const FRAME_URLS = Object.keys(FRAME_MODULES)
  .sort()
  .map((key) => FRAME_MODULES[key] as string)

const byPartId = new Map<string, string>()
partsCatalogue.forEach((part: { id: string }, i: number) => {
  const middle = i * FRAMES_PER_PART + Math.floor(FRAMES_PER_PART / 2)
  const url = FRAME_URLS[middle]
  if (url) byPartId.set(part.id, url)
})

/** Undefined for a part the catalogue does not cover — the caller draws a
 *  placeholder rather than a broken image. */
export function thumbnailFor(partId: string): string | undefined {
  return byPartId.get(partId)
}
