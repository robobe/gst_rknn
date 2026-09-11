#!/usr/bin/env python3
"""Generate a deterministic NanoTracker smoke video and ground truth."""
from pathlib import Path
import csv

import cv2
import numpy as np

FRAMES, FPS = 500, 30
WIDTH, HEIGHT = 640, 360
BOX_W = BOX_H = 64
LEFT, Y = 20, (HEIGHT - BOX_H) // 2
RIGHT = WIDTH - BOX_W - LEFT
ROOT = Path(__file__).parent
VIDEO = ROOT.parents[2] / "assets" / "nanotracker" / "move_right_500.mp4"
GROUND_TRUTH = ROOT / "move_right_500.csv"


def main():
    VIDEO.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(VIDEO), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("Cannot create MP4; install an OpenCV build with an FFmpeg encoder")

    background = np.full((HEIGHT, WIDTH, 3), (25, 25, 25), dtype=np.uint8)
    for x in range(0, WIDTH, 32):
        cv2.line(background, (x, 0), (x, HEIGHT), (35, 35, 35), 1)
    for y in range(0, HEIGHT, 32):
        cv2.line(background, (0, y), (WIDTH, y), (35, 35, 35), 1)

    rng = np.random.default_rng(3)
    target = rng.integers(0, 256, (BOX_H, BOX_W, 3), dtype=np.uint8)
    cv2.circle(target, (32, 32), 20, (0, 220, 255), -1)
    cv2.line(target, (0, 0), (63, 63), (255, 255, 255), 3)
    cv2.line(target, (63, 0), (0, 63), (255, 0, 255), 3)

    with GROUND_TRUTH.open("w", newline="") as output:
        rows = csv.writer(output)
        rows.writerow(("frame", "pts_ns", "x", "y", "width", "height"))
        for frame in range(FRAMES):
            x = round(LEFT + (RIGHT - LEFT) * frame / (FRAMES - 1))
            image = background.copy()
            image[Y:Y + BOX_H, x:x + BOX_W] = target
            writer.write(image)
            rows.writerow((frame, frame * 1_000_000_000 // FPS, x, Y, BOX_W, BOX_H))
    writer.release()
    print(f"wrote {VIDEO}")
    print(f"wrote {GROUND_TRUTH}")


if __name__ == "__main__":
    main()
