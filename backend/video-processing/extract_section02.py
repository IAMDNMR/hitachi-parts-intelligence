"""Turn assets/source/section-02/aftersales-eco.mp4 into the rotation frames.

Backend/tooling only. Nothing here runs in the browser, and the source video
is opened read-only -- it is never rewritten.

WHAT COMES OUT
--------------
`sequence` is what the site actually uses: EVERY frame of the clip's usable
arc, cut out and written as a numbered WebP sequence. Scroll picks a frame
and the canvas draws it, so the machine genuinely rotates rather than
dissolving between stills.

`frames` writes the four state keyframes as full-quality PNGs plus a contact
sheet, into assets/source/section-02. Those are the review/source
deliverable; the website does not load them.

WHICH FRAMES ARE USABLE (0-70)
------------------------------
The clip is a single 240-frame orbit, but it is not uniform. survey.py
measured the machine's silhouette on all 240 and two things fall out:

  * From frame ~72 onward the boom leaves the top of the picture -- the
    source frame simply does not contain it, so no crop can bring it back.
  * From ~140 the camera is far enough away that the machine covers barely
    half the pixels it did at the start (110k vs 230k), so those frames
    cannot be intercut with the near ones without the machine changing size.

Frames 0-70 are the one run that is both uncropped and at constant size
(silhouette 211k-233k px, within ~10%). That is 71 frames of continuous
rotation, and it is the whole of what this clip can give at full quality.
Using the rest would mean showing a truncated boom or a machine that shrinks
mid-scroll, which is worse than a shorter arc.

The four story states are keyed to frames 0, 23, 46 and 69 inside that run.

COMMON CROP
-----------
Every frame is cut with the *same* rectangle -- the union of the arc's
silhouettes plus a margin. No per-frame scaling, no per-frame centring. The
machine therefore sits exactly where the camera found it, and the rotation
is the only thing that changes.

WATERMARK
---------
The clip carries a four-point sparkle burned in at (1160, 600): fixed
position, present in every frame, about five grey levels above the floor it
sits on. It is an overlay, not part of the studio, and it lands on bare
floor well clear of the machine in all four chosen frames, so it is
inpainted. The HITACHI lettering, the decals and the warning labels are on
the machine itself and are left alone.

BACKGROUND
----------
Matting is the algorithm already proven on hero-sec.mp4 in
legacy/isolate-foreground.py -- same studio, same lighting. Summary: the
machine is either painted (saturated) or genuinely dark, and the room never
is, so a saturation-or-luminance rule separates them; what the machine
encloses is filled unless it looks like the room it happens to ring; edge
pixels get fractional alpha from their colour distance to a smooth fit of
the room and are then unmixed, so no grey rim survives.

If that produced a damaged silhouette the fallback would be to ship the
frames on their original studio background. It does not -- verify reports
coverage against the raw silhouette -- so the deliverables are transparent
PNGs.

Usage:
    python backend/video-processing/extract_section02.py sequence   # the site
    python backend/video-processing/extract_section02.py frames     # source PNGs
    python backend/video-processing/extract_section02.py verify
"""
import os
import shutil
import sys

import cv2
import numpy as np
import scipy.ndimage as nd
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-02', 'aftersales-eco.mp4')
SOURCE_DIR = os.path.join(ROOT, 'assets', 'source', 'section-02')
ROTATION_DIR = os.path.join(ROOT, 'assets', 'source', 'section-02', 'rotation')
DEBUG_DIR = os.path.join(os.path.dirname(__file__), 'debug')

# The usable arc: uncropped and at constant size. See the module docstring.
ARC = range(0, 71)
# The four story states, as indices into ARC.
PICKS = [0, 23, 46, 69]
PAD = 26                      # margin around the union silhouette, px
WEBP_QUALITY = 82             # visually lossless on this material at 936px

# Sparkle overlay: centre and radius, measured off the clip.
MARK = (1160, 600)
MARK_R = 34

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
SAT_T = 20            # above this a pixel is painted, so it is machine
LUMA_T = 112          # below this it is machine-dark; the room never is
MIN_COMPONENT = 150   # smaller islands are compression speckle
ERODE = 2             # inside this much of the core, alpha is solid
DILATE = 3            # beyond this much outside it, alpha is zero
D_LO, D_HI = 14.0, 48.0   # colour distance from the room -> fractional alpha
FIT_MIN_DIST = 45     # only room this far from the machine informs the fit
ROOM_FIT_TOL = 15.0   # an enclosed pocket this close to the room fit *is* room

# Colour the fully transparent field is flattened to. It is never visible;
# it only keeps the PNG's RGB plane from becoming unencodable noise.
FLAT = np.array([247, 247, 245], np.float32)


# --- source ---------------------------------------------------------------

def raw_machine(rgb):
    """The saturation-or-darkness rule, unsmoothed. Used for masks and checks."""
    luma = rgb @ LUMA
    sat = rgb.max(2) - rgb.min(2)
    return (sat > SAT_T) | (luma < LUMA_T)


def despeckle_mark(rgb):
    """Inpaint the burned-in sparkle, but never over the machine.

    Restricting the mask to pixels the machine rule does not claim means that
    if a future frame selection put the bucket over the sparkle, the bucket
    would be preserved and the sparkle simply left in place -- the machine is
    never the thing that gets repaired away.
    """
    h, w = rgb.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.circle(mask, MARK, MARK_R, 255, -1)
    mask[raw_machine(rgb.astype(np.float32))] = 0
    if not mask.any():
        return rgb.astype(np.float32)
    return cv2.inpaint(rgb, mask, 12, cv2.INPAINT_TELEA).astype(np.float32)


def read_frames(indices):
    """Decode the wanted frames as float RGB, watermark already removed."""
    want, out = set(indices), {}
    cap = cv2.VideoCapture(SRC)
    i = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if i in want:
            out[i] = despeckle_mark(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        i += 1
    cap.release()
    missing = want - set(out)
    if missing:
        raise SystemExit('frames not in clip: %s' % sorted(missing))
    return out


# --- matting (after legacy/isolate-foreground.py) -------------------------

def push_pull(value, weight):
    pyr_v, pyr_w = [value * weight[..., None]], [weight]
    h, w = value.shape[:2]
    while h > 4 and w > 4:
        h, w = (h + 1) // 2, (w + 1) // 2
        v = np.stack([np.asarray(Image.fromarray(pyr_v[-1][..., c]).resize((w, h), Image.BILINEAR)) for c in range(3)], -1)
        wt = np.asarray(Image.fromarray(pyr_w[-1]).resize((w, h), Image.BILINEAR))
        pyr_v.append(v)
        pyr_w.append(wt)
    out_v, out_w = pyr_v[-1], pyr_w[-1]
    for i in range(len(pyr_v) - 2, -1, -1):
        th, tw = pyr_w[i].shape
        up_v = np.stack([np.asarray(Image.fromarray(out_v[..., c]).resize((tw, th), Image.BILINEAR)) for c in range(3)], -1)
        up_w = np.asarray(Image.fromarray(out_w).resize((tw, th), Image.BILINEAR))
        a = np.clip(pyr_w[i], 0, 1)
        out_v = pyr_v[i] + (1 - a[..., None]) * up_v
        out_w = pyr_w[i] + (1 - a) * up_w
    return out_v / np.maximum(out_w[..., None], 1e-6)


def core_mask(rgb):
    """The machine's solid body: closed and de-speckled, but not hole-filled.

    Filling waits for fill_enclosed, which needs the room fit, which needs
    this. No morphological opening: opening at 3x3 erodes hydraulic hoses and
    handrails, which are only a few pixels wide. Speckle goes by discarding
    small components instead, which leaves thin structures intact because
    they are attached to something large.
    """
    core = raw_machine(rgb)
    core = nd.binary_closing(core, np.ones((5, 5)), iterations=2)
    lbl, cnt = nd.label(core)
    if cnt:
        sizes = nd.sum(core, lbl, range(1, cnt + 1))
        keep = np.zeros(cnt + 1, bool)
        keep[1:] = sizes >= MIN_COMPONENT
        core = keep[lbl]
    return core


def fill_enclosed(core, rgb, field):
    """Fill what the machine encloses -- but not the room it happens to ring.

    A blanket fill is what the silhouette needs to keep cab glass, chrome
    cylinder rods and pale body panels, none of which survive a luminance
    rule alone. But boom, arm and cab also ring a pocket of studio wall in
    most frames, and filling that welds a pale slab to the machine. Distance
    from the room fit separates them: real room sits within ~14 of the fit,
    machine interiors 40-80 away. Ties are filled -- keeping a little wall is
    a far cheaper mistake than losing part of the machine.
    """
    filled = nd.binary_fill_holes(core)
    holes = filled & ~core
    if not holes.any():
        return filled

    d = np.sqrt(((rgb - field) ** 2).sum(2))
    lbl, cnt = nd.label(holes)
    if not cnt:
        return filled

    room = np.zeros(cnt + 1, bool)
    means = nd.mean(d, lbl, range(1, cnt + 1))
    for k in range(1, cnt + 1):
        sel = lbl == k
        if sel.sum() < 200:
            continue  # too small to be a wall pocket; keep it filled
        if means[k - 1] < ROOM_FIT_TOL and np.median(d[sel]) < ROOM_FIT_TOL:
            room[k] = True
    return filled & ~room[lbl]


def cut(rgb):
    """One frame -> (decontaminated rgb, alpha 0..1)."""
    core = core_mask(rgb)

    # A smooth fit of the room, sampled well clear of the machine so the
    # machine's own shadow cannot pull the fit down. This is both the alpha
    # reference and the colour unmixed out of the edge pixels.
    dist_out = nd.distance_transform_edt(~core)
    known = (dist_out > FIT_MIN_DIST).astype(np.float32)
    field = push_pull(rgb, known) if known.sum() >= 5000 else np.full_like(rgb, 200.0)
    field = nd.gaussian_filter(field, (12, 12, 0))
    field = np.clip(field, 90.0, 255.0)

    core = fill_enclosed(core, rgb, field)

    inner = nd.binary_erosion(core, np.ones((3, 3)), iterations=ERODE)
    outer = nd.binary_dilation(core, np.ones((3, 3)), iterations=DILATE)

    d = np.sqrt(((rgb - field) ** 2).sum(2))
    a_edge = np.clip((d - D_LO) / (D_HI - D_LO), 0.0, 1.0)

    alpha = np.where(inner, 1.0, np.where(outer, a_edge, 0.0))
    alpha = nd.gaussian_filter(alpha, 0.6)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha[inner] = 1.0
    alpha[~outer] = 0.0

    # Unmix the room out of every partial pixel, so no grey rim survives.
    a3 = alpha[..., None]
    unmixed = np.clip((rgb - (1.0 - a3) * field) / np.maximum(a3, 0.08), 0, 255)
    out = np.where(a3 > 0.995, rgb, unmixed)
    out = np.where(alpha[..., None] > 0.02, out, FLAT)
    return out, alpha


# --- deliverables ---------------------------------------------------------

def common_crop():
    """One rectangle for the whole arc, so the machine does not drift.

    Measured from the cheap silhouette rule rather than from the finished
    mattes: holding 71 matted frames in memory to find a bounding box would
    cost most of a gigabyte, and the matte only ever extends a few pixels
    past the rule (DILATE), which PAD already covers several times over.
    """
    x0 = y0 = 10 ** 6
    x1 = y1 = 0
    cap = cv2.VideoCapture(SRC)
    h = w = 0
    for i in range(max(ARC) + 1):
        ok, bgr = cap.read()
        if not ok:
            break
        if i in ARC:
            h, w = bgr.shape[:2]
            m = raw_machine(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32))
            ys, xs = np.nonzero(m)
            x0, y0 = min(x0, int(xs.min())), min(y0, int(ys.min()))
            x1, y1 = max(x1, int(xs.max())), max(y1, int(ys.max()))
    cap.release()
    if not h:
        raise SystemExit('no frames read from %s' % SRC)
    return (max(x0 - PAD, 0), max(y0 - PAD, 0),
            min(x1 + PAD + 1, w), min(y1 + PAD + 1, h))


def sequence():
    """Cut every frame of the arc into the WebP sequence the site scrubs."""
    if os.path.isdir(ROTATION_DIR):
        shutil.rmtree(ROTATION_DIR)
    os.makedirs(ROTATION_DIR)

    box = common_crop()
    x0, y0, x1, y1 = box
    print('common crop: x %d-%d  y %d-%d  (%dx%d)' % (x0, x1, y0, y1, x1 - x0, y1 - y0))

    total = 0
    cap = cv2.VideoCapture(SRC)
    kept = 0
    for i in range(max(ARC) + 1):
        ok, bgr = cap.read()
        if not ok:
            break
        if i in ARC:
            rgb = despeckle_mark(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            fg, alpha = cut(rgb)
            rgba = np.concatenate([fg, alpha[..., None] * 255], 2)[y0:y1, x0:x1]
            im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
            path = os.path.join(ROTATION_DIR, 'frame-%03d.webp' % kept)
            im.save(path, quality=WEBP_QUALITY, method=6)
            total += os.path.getsize(path)
            kept += 1
            if kept % 10 == 0:
                print('  %d frames' % kept, flush=True)
        i += 1
    cap.release()
    print('%d frames, %.1f MB total, %.0f KB average -> %s'
          % (kept, total / 1e6, total / 1024.0 / max(kept, 1), ROTATION_DIR))
    return box


def build():
    """The four state keyframes as source PNGs, plus the review contact sheet."""
    os.makedirs(SOURCE_DIR, exist_ok=True)

    frames = read_frames(PICKS)
    cuts = [cut(frames[i]) for i in PICKS]
    x0, y0, x1, y1 = common_crop()
    print('common crop: x %d-%d  y %d-%d  (%dx%d)' % (x0, x1, y0, y1, x1 - x0, y1 - y0))

    for n, (rgb, alpha) in enumerate(cuts, 1):
        rgba = np.concatenate([rgb, alpha[..., None] * 255], 2)[y0:y1, x0:x1]
        im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
        name = 'hitachi-ecosystem-%02d.png' % n
        path = os.path.join(SOURCE_DIR, name)
        im.save(path, optimize=True)      # lossless; no resampling, no sharpening
        print('%-28s %5d x %4d  %6.0f KB' % (name, im.width, im.height,
                                             os.path.getsize(path) / 1024))

    contact_sheet(cuts, (x0, y0, x1, y1))


def contact_sheet(cuts, box):
    """Review-only sheet. The site never loads this file."""
    x0, y0, x1, y1 = box
    tw = 560
    th = int(round((y1 - y0) * tw / (x1 - x0)))
    sheet = Image.new('RGB', (tw * 2, (th + 34) * 2), (247, 247, 245))
    for n, (rgb, alpha) in enumerate(cuts):
        a3 = alpha[..., None]
        over = np.clip(rgb * a3 + FLAT * (1 - a3), 0, 255).astype(np.uint8)[y0:y1, x0:x1]
        tile = Image.fromarray(over).resize((tw, th), Image.LANCZOS)
        r, c = divmod(n, 2)
        sheet.paste(tile, (c * tw, r * (th + 34) + 34))

    d = ImageDraw.Draw(sheet)
    labels = ['01  MACHINE DATA  (src frame %d)' % PICKS[0],
              '02  PARTS  (src frame %d)' % PICKS[1],
              '03  SERVICE  (src frame %d)' % PICKS[2],
              '04  NETWORK  (src frame %d)' % PICKS[3]]
    for n, text in enumerate(labels):
        r, c = divmod(n, 2)
        d.text((c * tw + 14, r * (th + 34) + 12), text, fill=(31, 31, 31))
    path = os.path.join(SOURCE_DIR, 'contact-sheet.png')
    sheet.save(path)
    print('contact-sheet.png            %5d x %4d  (review only)' % sheet.size)


def verify():
    """Report how much of the raw silhouette the matte kept, plus debug maps."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    frames = read_frames(PICKS)
    for i in PICKS:
        rgb = frames[i]
        raw = raw_machine(rgb)
        _, alpha = cut(rgb)
        kept = (alpha[raw] > 0.5).mean()
        print('frame %3d  silhouette kept %6.3f%%   opaque px %7d   raw px %7d'
              % (i, kept * 100, int((alpha > 0.5).sum()), int(raw.sum())))
        Image.fromarray((alpha * 255).astype(np.uint8)).save(
            os.path.join(DEBUG_DIR, 'alpha-%03d.png' % i))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'sequence'
    if mode == 'sequence':
        sequence()
    elif mode == 'frames':
        build()
    elif mode == 'verify':
        verify()
    else:
        raise SystemExit('usage: extract_section02.py [sequence|frames|verify]')
