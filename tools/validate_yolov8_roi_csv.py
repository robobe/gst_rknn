#!/usr/bin/env python3
"""Validate YOLOv8 ROI CSV metadata against the Model Zoo bus.jpg reference."""

import argparse
import csv


REFERENCE = ((1, (211, 241, 283, 507), .873), (1, (109, 235, 225, 536), .866),
             (1, (476, 222, 560, 521), .863), (6, (99, 136, 550, 456), .859),
             (1, (80, 326, 116, 513), .311))


def iou(a, b):
    left, top, right, bottom = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    return overlap / (max(1, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    args = parser.parse_args()
    with open(args.csv, newline="") as source:
        rows = [{**row, "box": tuple(int(row[key]) for key in ("x", "y", "width", "height"))} for row in csv.DictReader(source) if row["roi_type"] == "yolo8"]
    failures = []
    for category, box, score in REFERENCE:
        expected = (box[0], box[1], box[2], box[3])
        candidates = [row for row in rows if row["class_id"] == str(category)]
        if not candidates:
            failures.append(f"missing COCO class {category}")
            continue
        best = max(candidates, key=lambda row: iou((row["box"][0], row["box"][1], row["box"][0] + row["box"][2], row["box"][1] + row["box"][3]), expected))
        actual = (best["box"][0], best["box"][1], best["box"][0] + best["box"][2], best["box"][1] + best["box"][3])
        overlap, delta = iou(actual, expected), abs(float(best["confidence"]) - score)
        print(f"class={category} box={actual} confidence={best['confidence']} iou={overlap:.3f} delta={delta:.3f}")
        if overlap < .8 or delta > .15: failures.append(f"class {category}: iou={overlap:.3f}, delta={delta:.3f}")
    assert not failures, "; ".join(failures)


if __name__ == "__main__":
    main()
