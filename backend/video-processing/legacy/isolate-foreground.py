"""Cut the excavator out of the studio clip as a true foreground layer.

The predecessor of this script (isolate-background.py) composited the studio
to page white. That kept the machine inside a rectangle: the page could only
ever be the one colour the clip had been graded to, and everything within
~78px of the silhouette kept a soft grey wash that read as a video frame.

This produces an *alpha* clip instead. The page owns the background, the
machine is a foreground object over it, and typography can pass behind it.

Segmentation. The machine is either saturated (orange paint) or genuinely
dark (tracks, cab, glass, bucket): its blacks sit around 20-60, while the
studio never falls below about 145 even in its shadowed corner. A luminance
rule is safe in that gap. Closing plus a hole fill then protects everything
the machine encloses -- chrome cylinder rods, cab glass, the light panels of
the separated cabs, the white HITACHI lettering.

That fill has to be selective, though. The machine also encloses *room*: the
boom, arm and cab ring a pocket of studio wall in nearly every frame, and
filling it keeps a slab of wall as opaque foreground, which on a light page
reads as a pale panel welded to the machine. See fill_enclosed.

Unlike the predecessor there is no morphological opening: opening at 3x3
erodes hydraulic hoses, which are only a few pixels wide. Speckle is removed
by discarding small connected components instead, which leaves thin
structures intact because they are attached to something large.

Matting. A hard mask would alias, and -- worse -- every edge pixel is a blend
of machine and studio grey. Composited onto a light page that leftover grey
reads as a dark outline. So edge pixels get a fractional alpha from their
colour distance to a smooth fit of the room, and are then decontaminated:
solving C = a*F + (1-a)*B for F recovers the machine's own colour and the
outline goes away.

No shadow is baked in. Grounding is the page's job (CSS), not the clip's.
"""
import os
import sys
import subprocess
import numpy as np
from PIL import Image
import scipy.ndimage as nd

SRC = os.path.join('assets', 'source', '_legacy', 'hero-sec.mp4')
WEBM = 'public/media/hero-excavator.webm'
MP4 = 'public/media/hero-excavator.mp4'
W, H = 1280, 720
DELOGO = 'delogo=x=1128:y=566:w=70:h=68'
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
FB = W * H * 3

# The page ground. The no-alpha fallback is composited onto exactly this, so
# that browsers without VP9 alpha still show no rectangle.
PAGE_BG = np.array([247, 247, 245], np.float32)

SAT_T = 20            # above this a pixel is painted, so it is machine
LUMA_T = 112          # below this it is machine-dark; the room never is
MIN_COMPONENT = 150   # smaller islands are compression speckle
ERODE = 2             # inside this much of the core, alpha is solid
DILATE = 3            # beyond this much outside it, alpha is zero
D_LO, D_HI = 14.0, 48.0   # colour distance from the room -> fractional alpha
FIT_MIN_DIST = 45     # only room this far from the machine informs the fit
ROOM_FIT_TOL = 15.0   # an enclosed pocket this close to the room fit *is* room


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
    """The machine's solid body: closed and de-speckled, but NOT hole-filled.

    Filling happens later, in `fill_enclosed`, because deciding what an
    enclosed region *is* needs the room fit, and the room fit needs this.
    """
    luma = rgb @ LUMA
    sat = rgb.max(2) - rgb.min(2)

    core = (sat > SAT_T) | (luma < LUMA_T)
    core = nd.binary_closing(core, np.ones((5, 5)), iterations=2)

    # The studio has dark fixtures near the ceiling. The machine never reaches
    # the top-left corner in any frame of this clip, so a dark *neutral* blob
    # there is set dressing -- unless it is painted.
    corner = np.zeros_like(core)
    corner[:105, :140] = True
    core &= ~(corner & (sat <= SAT_T))

    lbl, cnt = nd.label(core)
    if cnt:
        sizes = nd.sum(core, lbl, range(1, cnt + 1))
        keep = np.zeros(cnt + 1, bool)
        keep[1:] = sizes >= MIN_COMPONENT
        core = keep[lbl]
    return core


def fill_enclosed(core, rgb, field):
    """Fill what the machine encloses -- but not the room it happens to ring.

    A blanket hole fill is what a silhouette needs to keep cab glass, chrome
    cylinder rods and light body panels, all of which are too bright and too
    grey to survive a luminance rule on their own. But the machine also
    *encloses room*: the boom, arm and cab ring a pocket of studio wall in
    almost every frame, and filling that keeps a slab of the studio as opaque
    foreground. On a light page it reads as a pale panel welded to the
    machine -- the exact rectangle this pipeline exists to remove.

    Brightness cannot tell the two apart, because a grey body panel and a
    grey wall are both bright and both unsaturated. Distance from the room
    fit can: measured over this clip, genuine room sits within about 14 of
    the fit (95th percentile ~11-14) while machine interiors sit 40-80 away.
    So a pocket that looks like the room is left open, and everything else is
    filled -- erring toward filling, because losing part of the machine is
    far worse than keeping a little wall.
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

    # A smooth fit of the room, sampled well clear of the machine so its own
    # shadow cannot pull the fit down. This is both the alpha reference and
    # the colour we unmix out of the edge pixels.
    dist_out = nd.distance_transform_edt(~core)
    known = (dist_out > FIT_MIN_DIST).astype(np.float32)
    if known.sum() < 5000:
        field = np.full_like(rgb, 200.0)
    else:
        field = push_pull(rgb, known)
    field = nd.gaussian_filter(field, (12, 12, 0))
    field = np.clip(field, 90.0, 255.0)

    # Now that the room is characterised, decide what the machine encloses.
    # Doing it in this order also improves the fit: pockets of room ringed by
    # the machine are still room, and they inform it.
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

    # Below a couple of percent the pixel contributes nothing to the composite,
    # so its colour is free -- and it must be *spent* on flatness. Dividing by
    # a near-zero alpha turns the whole transparent field into high-entropy
    # noise, and a codec still has to encode rubbish it cannot show: leaving it
    # in put this clip over 30MB. Flat fill takes it to a few.
    out = np.where(alpha[..., None] > 0.02, out, PAGE_BG)
    return out, alpha


def frames():
    dec = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-i', SRC, '-vf', DELOGO,
         '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        stdout=subprocess.PIPE, bufsize=FB)
    while True:
        buf = dec.stdout.read(FB)
        if len(buf) < FB:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    dec.stdout.close()
    dec.wait()


def preview(indices):
    """Composite selected frames onto the page ground for inspection."""
    want = set(indices)
    for i, rgb in enumerate(frames()):
        if i not in want:
            continue
        fg, alpha = cut(rgb)
        a3 = alpha[..., None]
        over = np.clip(fg * a3 + PAGE_BG * (1 - a3), 0, 255).astype(np.uint8)
        Image.fromarray(over).save('preview_%03d_on_page.png' % i)
        Image.fromarray((alpha * 255).astype(np.uint8)).save('preview_%03d_alpha.png' % i)
        rgba = np.concatenate([fg, alpha[..., None] * 255], 2)
        Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA').save('preview_%03d_rgba.png' % i)
        print('preview', i, flush=True)


def sequence(step=1, quality=80,
             out_dir='assets/source/_legacy/machine-frames'):
    """Write the cut-out as a numbered image sequence.

    The hero scrubs by scroll position, and a <video> is a poor fit for that:
    a seek is a request, not a guarantee. It can be dropped while the decoder
    is busy, it lands on the nearest frame the codec can reach rather than the
    one asked for, and it depends on the browser having VP9 alpha at all. A
    sequence has none of those problems -- frame N is simply frame N, in every
    browser, with real per-frame alpha.

    The cost is bytes, so `step` exists: taking every other frame halves the
    payload, and scrubbing tolerates it well because the reader sets the pace.
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):
        if name.startswith('frame-') and name.endswith('.webp'):
            os.remove(os.path.join(out_dir, name))

    kept = 0
    total = 0
    for i, rgb in enumerate(frames()):
        if i % step:
            continue
        fg, alpha = cut(rgb)
        rgba = np.concatenate([fg, alpha[..., None] * 255], 2)
        im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
        path = os.path.join(out_dir, 'frame-%03d.webp' % kept)
        im.save(path, quality=quality, method=6)
        total += os.path.getsize(path)
        kept += 1
        if kept % 24 == 0:
            print('frame', kept, flush=True)
    print('wrote %d frames, %.1f MB total, %.0f KB average -> %s'
          % (kept, total / 1e6, total / 1024.0 / max(kept, 1), out_dir))
    return kept


def encode():
    """Write both deliverables in one pass over the source."""
    webm = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba',
         '-s', '%dx%d' % (W, H), '-r', '24', '-i', '-', '-an',
         '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p',
         # Scroll writes currentTime directly, so seeks must stay cheap. A
         # keyframe every quarter second costs at most five frames of decode
         # to land anywhere, which is imperceptible while scrubbing. Making
         # every frame a keyframe (as the H.264 copy does) is affordable in
         # AVC but not here: VP9 intra frames plus a full-resolution alpha
         # plane put the file over 60MB, which is not a hero asset.
         '-g', '6', '-auto-alt-ref', '0', '-lag-in-frames', '25',
         '-crf', '33', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2',
         '-deadline', 'good', '-cpu-used', '1', WEBM],
        stdin=subprocess.PIPE)
    mp4 = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', '%dx%d' % (W, H), '-r', '24', '-i', '-', '-an', '-c:v', 'libx264',
         '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-g', '1', '-keyint_min', '1',
         '-sc_threshold', '0', '-crf', '19', '-preset', 'slow',
         '-movflags', '+faststart', MP4],
        stdin=subprocess.PIPE)

    n = 0
    for rgb in frames():
        fg, alpha = cut(rgb)
        a3 = alpha[..., None]
        rgba = np.concatenate([fg, a3 * 255], 2)
        webm.stdin.write(np.clip(rgba, 0, 255).astype(np.uint8).tobytes())
        flat = fg * a3 + PAGE_BG * (1 - a3)
        mp4.stdin.write(np.clip(flat, 0, 255).astype(np.uint8).tobytes())
        n += 1
        if n % 24 == 0:
            print('frame', n, flush=True)

    webm.stdin.close()
    webm.wait()
    mp4.stdin.close()
    mp4.wait()
    print('done', n, '->', WEBM, MP4)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'sequence'
    if mode == 'preview':
        preview([int(a) for a in sys.argv[2:]] or [0, 96, 191])
    elif mode == 'sequence':
        # sequence [step] [quality]
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        quality = int(sys.argv[3]) if len(sys.argv) > 3 else 80
        sequence(step=step, quality=quality)
    elif mode == 'video':
        encode()
    else:
        raise SystemExit('usage: isolate-foreground.py [sequence|preview|video]')
