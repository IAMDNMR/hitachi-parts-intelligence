"""Edit assets/source/section-01/section-1.mp4 down to the Hero's sequence.

Backend/tooling only. The source video is opened read-only and never
rewritten; this writes a NEW sequence under assets/source/section-01/.

WHAT THE CLIP CONTAINS
----------------------
192 frames, 24fps, 8s, 1920x1080. One continuous exploded-view animation of
a Hitachi excavator against a light studio, with the camera slowly pushing
in throughout.

Two measurements were needed to read it, because the obvious one lies. The
subject's bounding box grows from 765px to 1750px and ends at 1407px, which
looks like a machine that never reassembles -- but it is complete again by
frame 180. The box is wide at the end because the camera pushed in, not
because the machine is still apart. Counting *separate components* of the
subject mask is scale-invariant and gives the true story:

    000-036  COMPLETE      whole machine, 2 components throughout
    037-110  SEPARATION    parts slide apart; components 2 -> 12
    111-147  EXPLODED      peak dispersion, 12-16 components; a dead hold
                           sits at 138-143 where the animation pauses
    148-166  REASSEMBLY    components return; back to 2 by ~165
    167-191  COMPLETE      whole machine again, larger in frame

HOW FRAMES ARE CHOSEN
---------------------
Not every Nth frame. Each phase is sampled at equal intervals of cumulative
frame-to-frame difference, so the static hold at 138-143 accumulates almost
no distance and costs almost no frames, while the fast separation and
reassembly get sampled densely. The first and last frame of the clip are
pinned so the sequence opens and closes on the complete machine.

OUTPUT FORMAT
-------------
1280x720 RGB WebP -- deliberately identical to the Hero's existing frames.
Section 01 is frozen: its canvas backing store is 1280x720 and its backdrop
samples the top and bottom strips of whatever image it is given, so matching
the current format exactly means the Hero needs no change beyond the path it
globs. The source is 1920x1080, but the canvas is 1280x720, so shipping the
larger frames would triple the bytes for pixels the Hero cannot draw.

Usage:
    python backend/video-processing/select_section01.py
"""
import json
import os
import shutil

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-01', 'section-1.mp4')
OUT_DIR = os.path.join(ROOT, 'assets', 'source', 'section-01', 'hero-frames')
MAP_PATH = os.path.join(ROOT, 'assets', 'source', 'section-01', 'hero-frame-map.json')

OUT_W, OUT_H = 1280, 720
WEBP_QUALITY = 86          # the Hero is the first thing anyone sees

# The generator's four-point sparkle, in SOURCE (1920x1080) coordinates. It
# is removed before the resize so the repair happens at full resolution.
WM = (820, 990, 1640, 1850)   # y0, y1, x0, x1

# Phase -> inclusive source range, and how many frames to keep.
PHASES = [
    ('complete',    'Complete machine',   0,  36, 18),
    ('separation',  'Separation',        37, 110, 25),
    ('exploded',    'Exploded state',   111, 147, 17),
    ('reassembly',  'Reassembly',       148, 166, 16),
    ('completeEnd', 'Machine restored', 167, 191, 14),
]


def sparkle_profile(frames):
    """The watermark's additive profile, estimated from the clip itself.

    The mark is a fixed overlay, so in each frame the patch is
    (content + sparkle). Subtracting a local median blur leaves
    high-frequency content plus the sparkle; the content changes frame to
    frame while the sparkle does not, so a per-pixel median across all 192
    frames isolates it. Subtracting that profile lifts the mark out without
    touching the studio gradient underneath -- which is why this is used
    rather than inpainting, whose smear would be worse than the mark.
    """
    y0, y1, x0, x1 = WM
    res = []
    for f in frames:
        patch = f[y0:y1, x0:x1]
        res.append(patch.astype(np.float32)
                   - cv2.medianBlur(patch, 31).astype(np.float32))
    return np.median(np.stack(res), axis=0)


def unwatermark(bgr, profile):
    y0, y1, x0, x1 = WM
    out = bgr.astype(np.float32)
    out[y0:y1, x0:x1] -= profile
    return np.clip(out, 0, 255).astype(np.uint8)


def read_all():
    cap = cv2.VideoCapture(SRC)
    frames = []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append(bgr)
    cap.release()
    return frames


def motion_curve(frames, indices):
    small = [cv2.resize(cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY), (160, 90),
                        interpolation=cv2.INTER_AREA).astype(np.float32)
             for i in indices]
    cum = [0.0]
    for a, b in zip(small, small[1:]):
        cum.append(cum[-1] + float(np.abs(b - a).mean()))
    return np.array(cum)


def pick_by_motion(frames, lo, hi, count, pin_first=False, pin_last=False):
    """Choose `count` frames from lo..hi at equal intervals of motion."""
    pool = list(range(lo, hi + 1))
    if len(pool) <= count:
        return pool

    cum = motion_curve(frames, pool)
    total = cum[-1]
    if total <= 0:
        step = (len(pool) - 1) / (count - 1.0)
        return [pool[int(round(k * step))] for k in range(count)]

    chosen = []
    for k in range(count):
        target = total * k / (count - 1.0)
        chosen.append(pool[int(np.argmin(np.abs(cum - target)))])

    if pin_first:
        chosen[0] = pool[0]
    if pin_last:
        chosen[-1] = pool[-1]

    # Equal motion steps can land twice where the animation pauses; move a
    # duplicate to its nearest unused neighbour, forward first then back.
    seen, out = set(), []
    for i in chosen:
        if i in seen:
            at = pool.index(i)
            alt = None
            for step in range(1, len(pool)):
                for cand in (at + step, at - step):
                    if 0 <= cand < len(pool) and pool[cand] not in seen:
                        alt = pool[cand]
                        break
                if alt is not None:
                    break
            if alt is None:
                continue
            i = alt
        seen.add(i)
        out.append(i)
    return sorted(out)


def main():
    frames = read_all()
    print('source: %d frames, %dx%d'
          % (len(frames), frames[0].shape[1], frames[0].shape[0]))
    profile = sparkle_profile(frames)
    print('watermark profile estimated (peak +%.0f); subtracting from every frame'
          % profile.max())
    frames = [unwatermark(f, profile) for f in frames]

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    phases_out = {}
    mapping = []
    n = 0
    for idx, (key, label, lo, hi, want) in enumerate(PHASES):
        picks = pick_by_motion(frames, lo, hi, want,
                               pin_first=(idx == 0),
                               pin_last=(idx == len(PHASES) - 1))
        start = n + 1
        for src_i in picks:
            n += 1
            bgr = cv2.resize(frames[src_i], (OUT_W, OUT_H),
                             interpolation=cv2.INTER_AREA)
            Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).save(
                os.path.join(OUT_DIR, 'frame-%03d.webp' % n),
                quality=WEBP_QUALITY, method=6)
            mapping.append({'output': n, 'source': src_i, 'phase': key})
        phases_out[key] = {'start': start, 'end': n, 'label': label,
                           'sourceRange': [lo, hi]}
        gaps = [b - a for a, b in zip(picks, picks[1:])]
        print('%-17s src %3d-%-3d -> frames %2d-%-2d  (%2d kept of %2d, gap %d-%d)'
              % (label, lo, hi, start, n, len(picks), hi - lo + 1,
                 min(gaps), max(gaps)))

    with open(MAP_PATH, 'w') as fh:
        json.dump({'source': 'assets/source/section-01/section-1.mp4',
                   'sourceFrames': len(frames),
                   'outputFrames': n,
                   'outputSize': [OUT_W, OUT_H],
                   'phases': phases_out,
                   'frames': mapping}, fh, indent=2)

    size = sum(os.path.getsize(os.path.join(OUT_DIR, f))
               for f in os.listdir(OUT_DIR))
    print()
    print('%d frames, %.1f MB -> %s' % (n, size / 1e6, OUT_DIR))
    print('map -> %s' % MAP_PATH)


if __name__ == '__main__':
    main()
