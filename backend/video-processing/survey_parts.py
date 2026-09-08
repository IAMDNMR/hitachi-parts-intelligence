"""Survey the Section 03 source clip before deciding anything about it.

The brief says the clip contains ten parts and that their names must come
from the clip rather than from guesswork. So this reads the clip twice:

  survey-parts/grid-*.png   every 4th frame tiled and labelled, so the whole
                            clip can be read in a couple of images
  survey-parts/cuts.csv     per-frame difference from the previous frame,
                            which is where the boundaries between one part
                            and the next show up as spikes

Nothing here writes into src/ or assets/, and the source video is opened
read-only.
"""
import csv
import os

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'source', 'section-03', 'parts-video.mp4')
OUT = os.path.join(os.path.dirname(__file__), 'survey-parts')


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
        small = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (160, 90),
                           interpolation=cv2.INTER_AREA).astype(np.float32)
        diff = 0.0 if prev is None else float(np.abs(small - prev).mean())
        prev = small
        # How much of the frame is subject rather than the light ground.
        ink = float((small < 200).mean())
        rows.append([idx, round(diff, 3), round(ink, 4)])
        frames.append(bgr)
        idx += 1
    cap.release()

    with open(os.path.join(OUT, 'cuts.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['frame', 'diff_prev', 'ink'])
        w.writerows(rows)

    picks = list(range(0, len(frames), 4))
    per, cols = 30, 6
    tw, th = 320, 180
    for sheet in range(0, len(picks), per):
        chunk = picks[sheet:sheet + per]
        rowsn = (len(chunk) + cols - 1) // cols
        canvas = np.full((rowsn * th, cols * tw, 3), 255, np.uint8)
        for i, f in enumerate(chunk):
            t = cv2.resize(frames[f], (tw, th), interpolation=cv2.INTER_AREA)
            cv2.putText(t, str(f), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255), 2, cv2.LINE_AA)
            r, c = divmod(i, cols)
            canvas[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t
        cv2.imwrite(os.path.join(OUT, 'grid-%02d.png' % (sheet // per)), canvas)

    # The biggest jumps are the candidate boundaries between parts.
    top = sorted(rows, key=lambda r: -r[1])[:24]
    print('%d frames' % len(frames))
    print('largest frame-to-frame changes (candidate cuts):')
    for f, d, ink in sorted(top):
        print('  frame %3d  diff %6.2f  ink %.3f' % (f, d, ink))


if __name__ == '__main__':
    main()
