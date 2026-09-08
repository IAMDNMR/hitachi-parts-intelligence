"""Turn assets/source/section-03/parts-video.mp4 into the Section 03 sequence.

Backend/tooling only. Nothing here runs in the browser, and the source video
is opened read-only.

WHAT THE CLIP IS
----------------
240 frames, ten parts, each turning on the spot for ~24 frames against a
white studio. PER_PART of each part's frames are kept, evenly spaced. survey_parts.py found the boundaries by frame-to-frame
difference: nine spikes of 22-41 against a bed of <3, at frames 22, 46, 72,
96, 120, 144, 168, 190 and 214. Those are the ten segments in SEGMENTS
below, and the part names were read off the frames themselves rather than
guessed — see data/partsCatalogue.js for the list.

ONE CROP FOR THE WHOLE CLIP
---------------------------
Measured per segment, every part is already shot at a similar size (603-832
px wide, 469-591 tall) and centred on roughly the same point. So a single
crop -- the union of all 240 silhouettes plus a margin -- holds every part
without rescaling any of them. The canvas box therefore never changes shape,
nothing jumps at a cut, and the parts keep their true relative sizes.

BACKGROUND
----------
This studio is flat: the border of every frame sits at 251-255 and 74.5% of
each frame is >=250, with only ~0.3% anywhere between 230 and 250. That gap
means a luminance key is safe here, and no fitted background field is needed
(unlike the excavator clip, whose studio had real shading).

Two things the naive version of that would get wrong, both handled below:

  * Specular highlights. Polished aluminium -- the controller especially --
    has blown-out patches that key out as background and punch holes in the
    part.
  * Genuine openings. The swing bearing is a ring, the track is a loop, the
    bucket is open. Blanket hole-filling would weld a white disc into the
    middle of them.

fill_enclosed tells the two apart by what the hole looks like: near-white
enclosed regions are the studio showing through and stay open; anything
darker is a highlight on the part and gets filled.

Usage:
    python backend/video-processing/extract_section03.py frames
    python backend/video-processing/extract_section03.py verify
"""
import os
import shutil
import sys

import cv2
import numpy as np
import scipy.ndimage as nd
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-03', 'parts-video.mp4')
OUT_DIR = os.path.join(ROOT, 'assets', 'source', 'section-03', 'parts-frames')
DEBUG_DIR = os.path.join(os.path.dirname(__file__), 'debug-parts')

# First frame of each part, plus the end. From survey_parts.py.
SEGMENTS = [0, 22, 46, 72, 96, 120, 144, 168, 190, 214, 240]

PER_PART = 9          # frames kept per part -> 90 in the sequence
PAD = 18              # margin around each part, px
ASPECT = 1.45         # shared crop shape, so the canvas box never changes
WEBP_QUALITY = 80

CORE_T = 238          # below this a pixel is certainly part, never studio
D_LO, D_HI = 3.0, 26.0    # distance below the studio white -> fractional alpha
MIN_COMPONENT = 60    # smaller islands are compression speckle
SMALL_HOLE = 80       # holes under this are noise; fill them regardless
HOLE_STUDIO_T = 246   # an enclosed region this bright IS the studio

# Colour the fully transparent field is flattened to. Never visible; it only
# keeps the WebP's colour plane from becoming unencodable noise.
FLAT = np.array([250, 249, 246], np.float32)


def studio_white(rgb):
    """The background level, read from the frame's own border."""
    b = np.concatenate([
        rgb[:6, :].reshape(-1, 3), rgb[-6:, :].reshape(-1, 3),
        rgb[:, :6].reshape(-1, 3), rgb[:, -6:].reshape(-1, 3),
    ])
    return np.median(b, axis=0).astype(np.float32)


def core_mask(grey):
    """The part's solid body: closed and de-speckled, not yet hole-filled."""
    core = grey < CORE_T
    core = nd.binary_closing(core, np.ones((5, 5)), iterations=2)
    lbl, cnt = nd.label(core)
    if cnt:
        sizes = nd.sum(core, lbl, range(1, cnt + 1))
        keep = np.zeros(cnt + 1, bool)
        keep[1:] = sizes >= MIN_COMPONENT
        core = keep[lbl]
    return core


def fill_enclosed(core, grey):
    """Fill highlights the part encloses; leave the studio it rings alone.

    The bearing is a ring, the track is a loop and the bucket is open, so a
    blanket fill would weld a white slab into the middle of three of the ten
    parts. Brightness separates them cleanly on this clip: studio pockets sit
    at 251-255, while even a blown highlight on machined metal has structure
    below HOLE_STUDIO_T somewhere in it, so its median lands lower.
    """
    filled = nd.binary_fill_holes(core)
    holes = filled & ~core
    if not holes.any():
        return filled

    lbl, cnt = nd.label(holes)
    if not cnt:
        return filled

    studio = np.zeros(cnt + 1, bool)
    for k in range(1, cnt + 1):
        sel = lbl == k
        if sel.sum() < SMALL_HOLE:
            continue  # too small to be an opening; filling it is invisible
        if np.median(grey[sel]) >= HOLE_STUDIO_T:
            studio[k] = True

    return filled & ~studio[lbl]


def cut(rgb):
    """One frame -> (decontaminated rgb, alpha 0..1)."""
    grey = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    bg = studio_white(rgb)

    core = fill_enclosed(core_mask(grey), grey)

    inner = nd.binary_erosion(core, np.ones((3, 3)), iterations=1)
    outer = nd.binary_dilation(core, np.ones((3, 3)), iterations=2)

    # Distance below the studio, so a pixel that is merely off-white gets a
    # fractional alpha rather than being forced to one or the other.
    d = np.sqrt(((rgb - bg) ** 2).sum(2))
    a_edge = np.clip((d - D_LO) / (D_HI - D_LO), 0.0, 1.0)

    alpha = np.where(inner, 1.0, np.where(outer, a_edge, 0.0))
    alpha = nd.gaussian_filter(alpha, 0.5)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha[inner] = 1.0
    alpha[~outer] = 0.0

    # Unmix the studio out of every partial pixel, so no white rim survives
    # when the part is composited onto a warm page.
    a3 = alpha[..., None]
    unmixed = np.clip((rgb - (1.0 - a3) * bg) / np.maximum(a3, 0.08), 0, 255)
    out = np.where(a3 > 0.995, rgb, unmixed)
    out = np.where(a3 > 0.02, out, FLAT)
    return out, alpha


def read_all():
    cap = cv2.VideoCapture(SRC)
    frames = []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32))
    cap.release()
    if len(frames) != SEGMENTS[-1]:
        raise SystemExit('expected %d frames, clip has %d'
                         % (SEGMENTS[-1], len(frames)))
    return frames


def segment_crops(frames):
    """One rectangle per part, all sharing a single aspect ratio.

    The previous version used one crop for all 240 frames: the union of every
    silhouette. That kept the parts at their true relative sizes, but it also
    meant every crop was sized for the largest of the ten. Measured on the
    result, a part filled only 43% of its own frame, and once the canvas was
    fitted into the page the part came out at about 5% of the viewport -- the
    smallest subject on the site, in the section built to showcase it.

    So each part now gets its own rectangle, and the ten rectangles are
    normalised to ASPECT by growing the short side about the part's centre.
    Two things follow. Each part fills its frame, so it lands on the page as
    large as the layout allows. And because every crop has the same shape,
    the canvas box never changes proportion between parts, so nothing jumps
    at a cut even though the rectangles differ in pixels.

    The cost is that the parts no longer show their true relative sizes -- a
    filter now appears about as large as a bucket. For ten separate products
    presented one at a time that is the right trade: this is a catalogue,
    where each item gets equal prominence, not a single machine being turned.
    """
    h, w = frames[0].shape[:2]
    luma = np.array([0.299, 0.587, 0.114], np.float32)
    crops = []

    for s_i in range(len(SEGMENTS) - 1):
        x0 = y0 = 10 ** 6
        x1 = y1 = 0
        for rgb in frames[SEGMENTS[s_i]:SEGMENTS[s_i + 1]]:
            ys, xs = np.nonzero((rgb @ luma) < CORE_T)
            x0, y0 = min(x0, int(xs.min())), min(y0, int(ys.min()))
            x1, y1 = max(x1, int(xs.max())), max(y1, int(ys.max()))

        # Grow the short side about the centre until the box is ASPECT.
        bw, bh = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        if bw / bh < ASPECT:
            bw = bh * ASPECT
        else:
            bh = bw / ASPECT
        bw += 2 * PAD
        bh += 2 * PAD

        # Keep it inside the frame: shift first, and only shrink if the frame
        # itself is too small, which would otherwise skew the aspect.
        bw, bh = min(bw, w), min(bh, h)
        cx = min(max(cx, bw / 2.0), w - bw / 2.0)
        cy = min(max(cy, bh / 2.0), h - bh / 2.0)

        crops.append((int(round(cx - bw / 2.0)), int(round(cy - bh / 2.0)),
                      int(round(cx + bw / 2.0)), int(round(cy + bh / 2.0))))
    return crops


def build():
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    frames = read_all()
    crops = segment_crops(frames)
    for i, (x0, y0, x1, y1) in enumerate(crops):
        print('part %2d crop: %4dx%-4d (aspect %.2f)'
              % (i + 1, x1 - x0, y1 - y0, (x1 - x0) / float(y1 - y0)))

    # Which source frames survive. The clip gives each part ~24 frames of a
    # slow turn, which is far more than the scroll can resolve: at this
    # section's height that was a frame every ~14px. PER_PART evenly spaced
    # frames per part read as the same rotation and cost a third of the
    # payload. Keeping the count identical for every part also means part i
    # simply owns frames [i*PER_PART, i*PER_PART + PER_PART - 1], so the
    # catalogue needs no hand-written frame indices.
    keep = []
    for k in range(len(SEGMENTS) - 1):
        a, b = SEGMENTS[k], SEGMENTS[k + 1]
        for j in range(PER_PART):
            keep.append((k, a + int(round(j * (b - a - 1) / (PER_PART - 1.0)))))

    total = 0
    fills = []
    for out_i, (seg, i) in enumerate(keep):
        rgb = frames[i]
        x0, y0, x1, y1 = crops[seg]

        fg, alpha = cut(rgb)
        rgba = np.concatenate([fg, alpha[..., None] * 255], 2)[y0:y1, x0:x1]
        a = rgba[..., 3]
        ys, xs = np.nonzero(a > 128)
        if len(xs):
            fills.append(((xs.max() - xs.min()) * (ys.max() - ys.min()))
                         / float(a.shape[0] * a.shape[1]))

        im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
        path = os.path.join(OUT_DIR, 'frame-%03d.webp' % out_i)
        im.save(path, quality=WEBP_QUALITY, method=6)
        total += os.path.getsize(path)
        if (out_i + 1) % 20 == 0:
            print('  %d frames' % (out_i + 1), flush=True)

    n = len(keep)
    print('%d frames, %.1f MB total, %.0f KB average -> %s'
          % (n, total / 1e6, total / 1024.0 / n, OUT_DIR))
    print('part fills its frame: %.0f%% of the crop area on average'
          % (100.0 * sum(fills) / max(len(fills), 1)))


def verify():
    """Check each part's matte: coverage, and that openings stayed open."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    frames = read_all()
    print('part  frame   kept%%   opaque px   holes kept (studio seen through)')
    for s in range(10):
        i = (SEGMENTS[s] + SEGMENTS[s + 1]) // 2
        rgb = frames[i]
        grey = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        raw = grey < CORE_T
        _, alpha = cut(rgb)
        solid = alpha > 0.5
        kept = (alpha[raw] > 0.5).mean() * 100
        # Studio still visible inside the part's convex outline = a real opening.
        opening = int((nd.binary_fill_holes(solid) & ~solid).sum())
        print('%4d  %5d  %6.2f  %10d   %d'
              % (s + 1, i, kept, int(solid.sum()), opening))
        Image.fromarray((alpha * 255).astype(np.uint8)).save(
            os.path.join(DEBUG_DIR, 'alpha-part-%02d.png' % (s + 1)))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'frames'
    if mode == 'frames':
        build()
    elif mode == 'verify':
        verify()
    else:
        raise SystemExit('usage: extract_section03.py [frames|verify]')
