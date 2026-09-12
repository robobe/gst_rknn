#!/usr/bin/env python3
"""Evaluate COCO predictions and write a durable Markdown benchmark report."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "assets" / "coco_val_sample")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "guides" / "yolov8-coco-val-sample.md")
    args = parser.parse_args()
    ground_truth = COCO(str(args.dataset / "annotations.json"))
    detections = ground_truth.loadRes(str(args.dataset / "predictions.json"))
    evaluation = COCOeval(ground_truth, detections, "bbox"); evaluation.evaluate(); evaluation.accumulate(); evaluation.summarize()
    benchmark = json.loads((args.dataset / "benchmark.json").read_text())
    args.output.write_text(f"# YOLOv8n RKNN COCO val sample\n\n"
                           f"- Date: {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n"
                           f"- Board: Radxa Zero 3W / RK3566\n"
                           f"- Runtime: RKNN 2.3.2\n"
                           f"- Model: `yolov8n-rk3566-int8.rknn` (Toolkit2 2.3.0 build)\n"
                           f"- Dataset: {benchmark['images']} deterministic COCO val2017 images (seed 20260912)\n\n"
                           f"| Metric | Result |\n| --- | ---: |\n"
                           f"| COCO mAP@[.50:.95] | {evaluation.stats[0]:.4f} |\n"
                           f"| AP@.50 | {evaluation.stats[1]:.4f} |\n"
                           f"| AP@.75 | {evaluation.stats[2]:.4f} |\n"
                           f"| RKNN inference FPS (after {benchmark['warmup_images']} warm-up images) | {benchmark['inference_fps']:.2f} |\n"
                           f"| End-to-end Python FPS | {benchmark['pipeline_fps']:.2f} |\n"
                           f"| Detections | {benchmark['detections']} |\n\n"
                           "Post-processing uses confidence 0.25 and per-class NMS IoU 0.45. "
                           "Keep these settings and the sample seed unchanged when comparing runs.\n")


if __name__ == "__main__": main()
