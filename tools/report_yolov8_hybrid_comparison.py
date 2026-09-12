#!/usr/bin/env python3
"""Compare paired INT8 and hybrid-INT8 COCO evaluation results."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("int8", "hybrid-int8")
TOOLKITS = {"int8": "2.3.2", "hybrid-int8": "2.3.2"}
HYBRID_FP16 = ("318", "onnx::ReduceSum_326", "331", "338", "onnx::ReduceSum_346", "350", "357", "onnx::ReduceSum_365", "369")


def evaluate(dataset, profile):
    ground_truth = COCO(str(dataset / "annotations.json"))
    result = COCOeval(ground_truth, ground_truth.loadRes(str(dataset / f"predictions-{profile}.json")), "bbox")
    result.evaluate(); result.accumulate(); result.summarize()
    return result.stats, json.loads((dataset / f"benchmark-{profile}.json").read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "assets" / "coco_val_sample")
    parser.add_argument("--models", type=Path, default=ROOT / "models" / "yolov8" / "rknn")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "guides" / "yolov8-hybrid-int8-comparison.md")
    args = parser.parse_args()
    results = {profile: evaluate(args.dataset, profile) for profile in PROFILES}
    int8_stats, int8_bench = results["int8"]
    hybrid_stats, hybrid_bench = results["hybrid-int8"]
    int8_default = int8_stats[0] >= hybrid_stats[0] and int8_bench["inference_fps"] >= hybrid_bench["inference_fps"]
    hybrid_default = hybrid_stats[0] > int8_stats[0] and hybrid_bench["inference_fps"] >= .85 * int8_bench["inference_fps"]
    rows = []
    for profile, (stats, benchmark) in results.items():
        model = args.models / f"yolov8n-rk3566-{profile}.rknn"
        rows.append(f"| {profile} | {TOOLKITS[profile]} | {model.stat().st_size / 1024 / 1024:.2f} | {stats[0]:.4f} | {stats[1]:.4f} | {stats[2]:.4f} | {benchmark['inference_fps']:.2f} | {benchmark['pipeline_fps']:.2f} | {benchmark['detections']} |")
    recommendation = "Recommend `int8`." if int8_default or not hybrid_default else "Recommend `hybrid-int8`."
    args.output.write_text(f"# YOLOv8n RK3566 INT8 vs hybrid-INT8\n\n"
                           f"- Date: {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n"
                           "- Board: Radxa Zero 3W / RK3566; Runtime: RKNN 2.3.2\n"
                           "- Source: Rockchip Model Zoo YOLOv8n ONNX commit `bad6c7334531becaf90a561988519b7bec34d0ab`, SHA-256 `0c8716701f471067932b797eeb67c8e5db47c693c2557c881d7679ec12e21bc5`\n"
                           "- Calibration: identical deterministic 200-image COCO train2017 sample, seed 20260912\n"
                           f"- Evaluation: {int8_bench['images']} deterministic COCO val2017 images, seed 20260912; confidence 0.25, per-class NMS IoU 0.45\n\n"
                           "| Profile | Toolkit build | Model MiB | mAP@[.50:.95] | AP@.50 | AP@.75 | RKNN inference FPS | End-to-end Python FPS | Detections |\n"
                           "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n" + "\n".join(rows) + "\n\n"
                           f"Hybrid FP16 output tensors: {', '.join(f'`{name}`' for name in HYBRID_FP16)}.\n\n"
                           f"Hybrid acceptance requires higher mAP@[.50:.95] and at least 85% of INT8 inference FPS ({.85 * int8_bench['inference_fps']:.2f} FPS). Pure INT8 is the default if it matches or beats hybrid mAP while remaining at least as fast. {recommendation}\n")
    print(recommendation)


if __name__ == "__main__":
    main()
