"""Survey the Section 04 source clip before selecting a single frame.

The brief for this clip is unusual: it says explicitly *not* to take every
Nth frame, and not to keep everything. So this measures the clip first and
produces material a human (or agent) can actually look at, rather than
deciding anything on its own.

Outputs, all under survey-s04/ and none of them shipped:

  grid-*.png   every 3rd frame tiled and labelled, so the whole clip can be
               read in a few images
  metrics.csv  per-frame measurements used to reason about the edit:

     diff_prev   mean abs difference from the previous frame. Spikes are
                 cuts; a long run of near-zero is a static hold.
     sharp       variance of the Laplacian. Low = soft or motion-blurred.
     ink         fraction of the frame that is not near-white background.
     edges       fraction of pixels on a Canny edge. A proxy for how much
                 structure — i.e. readable detail — a frame carries.
     dark        fraction below luma 40, to catch black frames / fades.

Nothing here writes into src/ or assets/, and the source video is opened
read-only.
"""
import csv
import os

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-04', 'section-4.mp4')
OUT = os.path.join(os.path.dirname(__file__), 'survey-s04')


def main():
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(SRC)
    frames, rows = [], []
    prev = None
    idx = 0

    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(grey, (160, 90), interpolation=cv2.INTER_AREA).astype(np.float32)

        diff = 0.0 if prev is None else float(np.abs(small - prev).mean())
        prev = small

        sharp = float(cv2.Laplacian(grey, cv2.CV_64F).var())
        ink = float((grey < 235).mean())
        edges = float((cv2.Canny(grey, 60, 160) > 0).mean())
        dark = float((grey < 40).mean())

        rows.append([idx, round(diff, 3), round(sharp, 1), round(ink, 4),
                     round(edges, 5), round(dark, 4)])
        frames.append(bgr)
        idx += 1
    cap.release()

    with open(os.path.join(OUT, 'metrics.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['frame', 'diff_prev', 'sharp', 'ink', 'edges', 'dark'])
        w.writerows(rows)

    # Contact grids: every 3rd frame, 6 x 5 per sheet, labelled.
    picks = list(range(0, len(frames), 3))
    per, cols = 30, 6
    tw, th = 320, 180
    for sheet in range(0, len(picks), per):
        chunk = picks[sheet:sheet + per]
        rowsn = (len(chunk) + cols - 1) // cols
        canvas = np.full((rowsn * th, cols * tw, 3), 255, np.uint8)
        for i, f in enumerate(chunk):
            t = cv2.resize(frames[f], (tw, th), interpolation=cv2.INTER_AREA)
            cv2.putText(t, str(f), (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 255), 2, cv2.LINE_AA)
            r, c = divmod(i, cols)
            canvas[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t
        cv2.imwrite(os.path.join(OUT, 'grid-%02d.png' % (sheet // per)), canvas)

    a = np.array([r[1] for r in rows])
    s = np.array([r[2] for r in rows])
    print('%d frames' % len(frames))
    print('diff_prev : median %.2f  p90 %.2f  max %.2f' % (np.median(a), np.percentile(a, 90), a.max()))
    print('sharp     : median %.0f  p10 %.0f  min %.0f' % (np.median(s), np.percentile(s, 10), s.min()))
    print()
    print('candidate cuts (diff_prev > 8):')
    print('  ' + ', '.join(str(i) for i, d in enumerate(a) if d > 8))
    print('softest frames (sharp in bottom 10%%):')
    print('  ' + ', '.join(str(i) for i in np.argsort(s)[:24]))
    print('most static runs (diff_prev < 0.5):')
    print('  ' + ', '.join(str(i) for i, d in enumerate(a) if d < 0.5))


if __name__ == '__main__':
    main()
