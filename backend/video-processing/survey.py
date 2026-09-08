"""Survey the Section 02 source clip before choosing anything.

Two outputs, both for human/agent inspection only -- neither ships:

  survey/grid-*.png   every 4th frame tiled, so the whole rotation can be
                      read in a couple of images
  survey/stats.csv    per-frame measurements used to reason about the clip:
                      how much of the frame is machine, where its silhouette
                      sits, and how different each frame is from the last.

Nothing here writes into assets/ and nothing touches the source video.
"""
import csv
import os

import cv2
import numpy as np

SRC = os.path.join('assets', 'source', 'section-02', 'aftersales-eco.mp4')
OUT = os.path.join('backend', 'video-processing', 'survey')

# The studio is a light room; the machine is either painted (saturated) or
# genuinely dark. Same rule the hero clip used -- see isolate.py for why.
SAT_T = 20
LUMA_T = 112


def machine_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return ((hsv[:, :, 1] > SAT_T) | (grey < LUMA_T)).astype(np.uint8)


def main():
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(SRC)
    frames, rows, prev = [], [], None
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        m = machine_mask(bgr)
        ys, xs = np.nonzero(m)
        if len(xs):
            box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        else:
            box = (0, 0, 0, 0)
        small = cv2.resize(m, (160, 90), interpolation=cv2.INTER_AREA)
        diff = 0.0 if prev is None else float(np.abs(small.astype(np.float32) - prev).mean())
        prev = small.astype(np.float32)
        rows.append([idx, int(m.sum()), *box, round(diff, 4)])
        frames.append(bgr)
        idx += 1
    cap.release()

    with open(os.path.join(OUT, 'stats.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['frame', 'machine_px', 'x0', 'y0', 'x1', 'y1', 'diff_prev'])
        w.writerows(rows)

    # Contact grids: every 4th frame, 6 x 5 per sheet, labelled with its index.
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
        cv2.imwrite(os.path.join(OUT, f'grid-{sheet // per:02d}.png'), canvas)

    print(f'{len(frames)} frames -> {OUT}')


if __name__ == '__main__':
    main()
