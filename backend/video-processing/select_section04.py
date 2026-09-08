"""Edit assets/source/section-04/section-4.mp4 into a service sequence.

Backend/tooling only. The source video is opened read-only and never
rewritten; this writes a NEW sequence under assets/source/section-04/.

WHAT THE CLIP ACTUALLY CONTAINS
-------------------------------
survey_section04.py measured all 240 frames (24fps, 10s, 1280x720). Four
distinct scenes, separated by three cross-dissolves:

    000-054  workshop wide  technician walks to and around the machine,
                            tablet in hand
    055-064  DISSOLVE       both scenes ghosted over each other
    065-087  close-up       technician at the open engine bay with a
                            diagnostic tablet
    088-095  DISSOLVE
    096-209  workshop wide  technician servicing the machine; drain pan,
                            oil filter and container on the floor
    210-219  DISSOLVE
    220-239  outdoor site   the machine working, second machine behind

The dissolve extents are measured, not eyeballed. A frame-difference spike
only finds a dissolve's steepest part -- it reported 55-62, 93-95 and 209-216,
and selecting against those left visibly ghosted frames at the edges of the
close-up. Correlating every frame against a clean anchor inside each
neighbouring scene finds the real extent: a dissolve frame resembles BOTH
scenes at once, while a clean frame resembles only its own. The ranges above
are where that dual similarity holds, padded by one frame at each end.

FIVE STAGES OUT OF FOUR SCENES
------------------------------
The brief asks for INSPECT / DIAGNOSE / MAINTAIN / REPAIR / BACK TO WORK.
The clip supplies four scenes, so MAINTAIN and REPAIR have to come out of
the single long workshop run. The honest split is by what the technician is
doing, which the frames do show:

    096-150  crouched low at the filter and drain pan  -> MAINTAIN
    151-209  standing, working along the upper structure and engine side
             -> REPAIR

That is the strongest available reading. It is *not* what the brief
describes as repair footage: there is no component removal, no tool
close-up and no replacement part anywhere in this clip. Reported rather
than faked -- see the note printed at the end of a run.

HOW FRAMES ARE CHOSEN
---------------------
Not every Nth frame, and not the sharpest hero frames either. Each stage is
sampled at equal intervals of *cumulative motion* rather than of time.

Frame-to-frame difference is summed across the stage to give a distance
along the action. Picking equally spaced points on that curve means a long
static hold accumulates almost no distance and therefore costs almost no
frames, while a passage where the technician actually moves gets sampled
densely. That is what keeps the result feeling like animation when scrubbed
instead of like a slideshow of poses.

Dissolve frames are excluded outright: they are double exposures of two
scenes and read as a fault. Frames well below their own scene's typical
sharpness are excluded too -- see SHARP_FRACTION for why that test is
relative rather than absolute.

THE WATERMARK
-------------
The clip carries a four-point sparkle burned in at (1160, 600) in all 240
frames. Inpainting it does not work: on the outdoor gravel Telea produces an
obvious smeared blob, visibly worse than the sparkle.

It is removed by subtraction instead. The sparkle is an *additive* overlay
in a fixed position, so its profile is the one component that survives a
per-pixel median of (frame - local median blur) taken across all 240 frames,
whose underlying content differs. Subtracting that profile takes the mark
out while leaving the floor gradient and the gravel texture underneath it
intact -- which is the whole reason inpainting failed.

Usage:
    python backend/video-processing/select_section04.py
"""
import json
import os
import shutil

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-04', 'section-4.mp4')
OUT_DIR = os.path.join(ROOT, 'assets', 'source', 'section-04', 'service-frames')
MAP_PATH = os.path.join(ROOT, 'assets', 'source', 'section-04', 'service-frame-map.json')

WEBP_QUALITY = 82

# Softness is judged against the scene the frame belongs to, not against an
# absolute number. Measured, the four scenes sit at very different levels --
# the diagnostic close-up has a median Laplacian variance of 28.6 because it
# is shot at shallow depth of field with a large out-of-focus panel behind
# the technician, while the outdoor scene sits at 251. An absolute floor set
# high enough to catch blur elsewhere rejected almost the whole close-up,
# which is soft by design rather than by fault. A fraction of the scene's own
# median catches genuine blur in every scene without punishing any of them.
SHARP_FRACTION = 0.72

# The sparkle watermark's patch and how strongly to subtract it.
WM = (545, 660, 1100, 1225)   # y0, y1, x0, x1

# Stage name -> inclusive source range, and how many frames to keep.
STAGES = [
    ('inspect',    'Inspect',      0,  54, 18),
    ('diagnose',   'Diagnose',    65,  87, 18),
    ('maintain',   'Maintain',    96, 150, 18),
    ('repair',     'Repair',     151, 209, 18),
    ('backToWork', 'Back to work', 220, 239, 18),
]

# Cross-dissolves. Excluded from every stage.
DISSOLVES = [(55, 64), (88, 95), (210, 219)]


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


def sparkle_profile(frames):
    """The watermark's additive profile, estimated from the clip itself.

    In each frame the mark is (content + sparkle). Subtracting a local median
    blur leaves high-frequency content plus the sparkle; the content differs
    frame to frame while the sparkle does not, so a per-pixel median across
    all 240 frames isolates the sparkle.
    """
    y0, y1, x0, x1 = WM
    res = []
    for f in frames:
        p = f[y0:y1, x0:x1].astype(np.float32)
        bg = cv2.medianBlur(f[y0:y1, x0:x1], 31).astype(np.float32)
        res.append(p - bg)
    return np.median(np.stack(res), axis=0)


def unwatermark(bgr, profile):
    y0, y1, x0, x1 = WM
    out = bgr.astype(np.float32)
    out[y0:y1, x0:x1] -= profile
    return np.clip(out, 0, 255).astype(np.uint8)


def sharpness(bgr):
    return cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()


def motion_curve(frames, indices):
    """Cumulative frame-to-frame difference along `indices`."""
    small = [cv2.resize(cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY), (160, 90),
                        interpolation=cv2.INTER_AREA).astype(np.float32)
             for i in indices]
    cum = [0.0]
    for a, b in zip(small, small[1:]):
        cum.append(cum[-1] + float(np.abs(b - a).mean()))
    return np.array(cum)


def pick_by_motion(frames, lo, hi, count):
    """Choose `count` frames from lo..hi at equal intervals of motion."""
    dissolve = set()
    for a, b in DISSOLVES:
        dissolve.update(range(a, b + 1))

    span = [i for i in range(lo, hi + 1) if i not in dissolve]
    sharp = np.array([sharpness(frames[i]) for i in span])
    floor = float(np.median(sharp)) * SHARP_FRACTION
    pool = [i for i, sv in zip(span, sharp) if sv >= floor]
    dropped_soft = len(span) - len(pool)
    if len(pool) <= count:
        return pool, dropped_soft

    cum = motion_curve(frames, pool)
    total = cum[-1]
    if total <= 0:                       # a completely static stage
        step = (len(pool) - 1) / (count - 1.0)
        return [pool[int(round(k * step))] for k in range(count)], dropped_soft

    chosen = []
    for k in range(count):
        target = total * k / (count - 1.0)
        chosen.append(pool[int(np.argmin(np.abs(cum - target)))])

    # Equal motion steps can land twice on the same frame where the action
    # pauses. Nudge duplicates onto the nearest unused neighbour, trying
    # forward first and then backward -- forward alone fails at the end of a
    # stage, which silently shipped frame 239 twice.
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
                continue          # pool genuinely exhausted
            i = alt
        seen.add(i)
        out.append(i)
    return sorted(out), dropped_soft


def main():
    frames = read_all()
    print('source: %d frames, %dx%d' % (len(frames), frames[0].shape[1], frames[0].shape[0]))
    profile = sparkle_profile(frames)
    print('watermark profile estimated (peak +%.0f); subtracting from every frame'
          % profile.max())
    frames = [unwatermark(f, profile) for f in frames]

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    stages_out = {}
    n = 0
    kept_total = []
    for key, label, lo, hi, want in STAGES:
        picks, soft = pick_by_motion(frames, lo, hi, want)
        start = n + 1
        for src_i in picks:
            n += 1
            rgb = cv2.cvtColor(frames[src_i], cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb).save(
                os.path.join(OUT_DIR, 'frame-%03d.webp' % n),
                quality=WEBP_QUALITY, method=6)
        stages_out[key] = {'start': start, 'end': n, 'label': label,
                           'sourceRange': [lo, hi]}
        kept_total.append((label, lo, hi, len(picks), soft, picks))
        print('%-13s src %3d-%-3d -> frames %2d-%-2d  (%d kept of %d)'
              % (label, lo, hi, start, n, len(picks), hi - lo + 1))

    with open(MAP_PATH, 'w') as fh:
        json.dump({'totalFrames': n,
                   'source': 'assets/source/section-04/section-4.mp4',
                   'sourceFrames': len(frames),
                   'stages': stages_out}, fh, indent=2)

    size = sum(os.path.getsize(os.path.join(OUT_DIR, f))
               for f in os.listdir(OUT_DIR))
    print()
    print('%d frames, %.1f MB -> %s' % (n, size / 1e6, OUT_DIR))
    print('map -> %s' % MAP_PATH)
    print()
    print('NOTE: this clip contains no component removal, tool close-up or')
    print('replacement part, so REPAIR uses the strongest available frames')
    print('(technician working along the upper structure) rather than real')
    print('repair footage. Nothing was invented to fill it.')


if __name__ == '__main__':
    main()
