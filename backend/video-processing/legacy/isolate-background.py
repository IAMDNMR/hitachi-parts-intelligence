"""Neutralise the studio behind the excavator, frame by frame.

Why per frame: the room is not static. Sampling the machine-free left strip
across the clip gives means of 164, 190 and 170 with the column profile
changing shape, so the camera/lighting moves. A single background plate
therefore cannot cancel the wall, and any attempt to subtract one leaves
edges behind.

Segmentation. The machine is either saturated (orange paint) or genuinely
dark (tracks, cab, glass, bucket) -- its blacks sit around 20-60, while the
studio never falls below about 145 even in its shadowed corner. That gap is
what makes a luminance rule safe here, provided the threshold sits in the gap
rather than at the room's own darkness. Morphological closing plus a
border-connected hole fill then protects everything the machine encloses:
chrome cylinder rods, cab glass, the light panels of the separated cabs.

Compositing, by distance from the machine:

  0-12 px    untouched. Anti-aliased edges, thin hoses and cables live here,
             and a damaged machine is worse than a visible wall.
  12-78 px   re-exposed against a smooth fit of the surrounding room, so the
             ambient tone flattens to white but the machine's contact shadow
             survives as a relative darkening.
  78 px +   pure page white. This is what removes the wall panel, the corner
             geometry, the ceiling junction, the wall/floor line and the broad
             floor gradient outright, edges included.

The result grounds the machine without putting it in a room.
"""
import os
import subprocess
import numpy as np
from PIL import Image
import scipy.ndimage as nd

SRC = os.path.join('assets', 'source', '_legacy', 'hero-sec.mp4')
DST = 'hero-isolated.mp4'
W, H, N = 1280, 720, 192
DELOGO = 'delogo=x=1128:y=566:w=70:h=68'
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
FB = W * H * 3

PROTECT_PX = 6       # untouched band hugging the machine, for edges
EDGE_FADE_PX = 10    # protect band fades to white over this
GROUND_PX = 46       # how far a contact shadow may reach below a part
FIT_MIN_DIST = 45    # only room this far from the machine informs the fit


def push_pull(value, weight):
    pyr_v, pyr_w = [value * weight[..., None]], [weight]
    h, w = value.shape[:2]
    while h > 4 and w > 4:
        h, w = (h + 1) // 2, (w + 1) // 2
        v = np.stack([np.asarray(Image.fromarray(pyr_v[-1][..., c]).resize((w, h), Image.BILINEAR)) for c in range(3)], -1)
        wt = np.asarray(Image.fromarray(pyr_w[-1]).resize((w, h), Image.BILINEAR))
        pyr_v.append(v); pyr_w.append(wt)
    out_v, out_w = pyr_v[-1], pyr_w[-1]
    for i in range(len(pyr_v) - 2, -1, -1):
        th, tw = pyr_w[i].shape
        up_v = np.stack([np.asarray(Image.fromarray(out_v[..., c]).resize((tw, th), Image.BILINEAR)) for c in range(3)], -1)
        up_w = np.asarray(Image.fromarray(out_w).resize((tw, th), Image.BILINEAR))
        a = np.clip(pyr_w[i], 0, 1)
        out_v = pyr_v[i] + (1 - a[..., None]) * up_v
        out_w = pyr_w[i] + (1 - a) * up_w
    return out_v / np.maximum(out_w[..., None], 1e-6)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


dec = subprocess.Popen(
    ['ffmpeg', '-v', 'error', '-i', SRC, '-vf', DELOGO,
     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
    stdout=subprocess.PIPE, bufsize=FB)
enc = subprocess.Popen(
    ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', '24', '-i', '-', '-an', '-c:v', 'libx264',
     '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-g', '1', '-keyint_min', '1',
     '-sc_threshold', '0', '-crf', '19', '-preset', 'slow',
     '-movflags', '+faststart', DST],
    stdin=subprocess.PIPE)

i = 0
while True:
    buf = dec.stdout.read(FB)
    if len(buf) < FB:
        break
    rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)

    luma = rgb @ LUMA
    sat = rgb.max(2) - rgb.min(2)

    core = (sat > 20) | (luma < 112)
    core = nd.binary_closing(core, np.ones((5, 5)), iterations=2)
    core = nd.binary_fill_holes(core)
    core = nd.binary_opening(core, np.ones((3, 3)))          # drop speckle

    # The studio has its own dark fixtures near the ceiling. The machine never
    # reaches the top-left corner in any frame of this clip, so a dark neutral
    # blob there is set dressing, not the excavator -- unless it is painted.
    corner = np.zeros_like(core)
    corner[:105, :140] = True
    core &= ~(corner & (sat <= 20))

    # Drop stray specks that survived; real components are far larger.
    lbl, cnt = nd.label(core)
    if cnt:
        sizes = nd.sum(core, lbl, range(1, cnt + 1))
        keep = np.zeros(cnt + 1, bool)
        keep[1:] = sizes >= 250
        core = keep[lbl]
    core = nd.binary_fill_holes(core)
    machine = nd.binary_dilation(core, np.ones((3, 3)), iterations=3)

    dist = nd.distance_transform_edt(~machine)

    # Per column, the lowest machine pixel: everything under it is floor, and
    # everything over it is wall. Columns with no machine get no shadow.
    rows = np.arange(H)[:, None]
    masked_rows = np.where(machine, rows, -1)
    bottom = masked_rows.max(0)                      # -1 where the column is empty
    below = (rows > (bottom[None, :] + 2)) & (bottom[None, :] >= 0)

    # Smooth fit of the room, from background well clear of the machine so the
    # machine's own shadow does not pull the fit down.
    known = (dist > FIT_MIN_DIST).astype(np.float32)
    if known.sum() < 5000:
        field = np.full_like(rgb, 235.0)
    else:
        field = push_pull(rgb, known)
    field = nd.gaussian_filter(field, (12, 12, 0))
    field = np.clip(field, 90.0, 255.0)

    normalised = np.clip(rgb / field * 255.0, 0, 255)

    # How much of the frame survives, rather than being replaced by white.
    edge_keep = 1.0 - smoothstep((dist - PROTECT_PX) / EDGE_FADE_PX)
    ground_keep = np.where(below, 1.0 - smoothstep((dist - PROTECT_PX) / GROUND_PX), 0.0)
    keep = np.maximum(edge_keep, ground_keep)
    keep = nd.gaussian_filter(keep, 3.0)
    keep[machine] = 1.0
    keep = keep[..., None]

    # Inside the mask the frame is untouched; outside it the room is
    # re-exposed so its ambient tone flattens, then faded into page white.
    to_norm = smoothstep((dist - 2) / 6.0)[..., None]
    body = rgb * (1 - to_norm) + normalised * to_norm
    out = body * keep + 255.0 * (1 - keep)
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())

    i += 1
    if i % 48 == 0:
        print('frame', i, flush=True)

dec.stdout.close(); dec.wait()
enc.stdin.close(); enc.wait()
print('done', i, '->', DST)
