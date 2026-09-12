#!/usr/bin/env python3
"""Run RKNN YOLOv8 over a COCO subset and save COCO detections plus FPS."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
from rknnlite.api import RKNNLite

from smoke_test import boxes_from_outputs


ROOT = Path(__file__).resolve().parents[3]
COCO_IDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 70, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 89, 90)


def letterbox(path):
    image = Image.open(path).convert("RGB")
    width, height = image.size
    scale = min(640 / width, 640 / height)
    resized = image.resize((round(width * scale), round(height * scale)))
    canvas = Image.new("RGB", (640, 640))
    left, top = (640 - resized.width) // 2, (640 - resized.height) // 2
    canvas.paste(resized, (left, top))
    return np.asarray(canvas)[None], (scale, left, top, width, height)


def nms(boxes, scores, classes, threshold=.45):
    kept = []
    for category in np.unique(classes):
        order = np.where(classes == category)[0][np.argsort(scores[classes == category])[::-1]]
        while len(order):
            current, order = order[0], order[1:]
            kept.append(current)
            if not len(order): continue
            overlap_left_top = np.maximum(boxes[current, :2], boxes[order, :2])
            overlap_right_bottom = np.minimum(boxes[current, 2:], boxes[order, 2:])
            overlap = np.prod(np.maximum(0, overlap_right_bottom - overlap_left_top), axis=1)
            areas = np.prod(boxes[current, 2:] - boxes[current, :2]) + np.prod(boxes[order, 2:] - boxes[order, :2], axis=1) - overlap
            order = order[overlap / areas <= threshold]
    return kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "assets" / "coco_val_sample")
    parser.add_argument("--profile", choices=("int8", "hybrid-int8"), default="int8")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--threshold", type=float, default=.25)
    args = parser.parse_args()
    if args.model is None:
        args.model = ROOT / "models" / "yolov8" / "rknn" / f"yolov8n-rk3566-{args.profile}.rknn"
    annotations = json.loads((args.dataset / "annotations.json").read_text())
    rknn, predictions, timings = RKNNLite(verbose=False), [], []
    try:
        assert rknn.load_rknn(str(args.model)) == 0 and rknn.init_runtime() == 0
        overall_start = time.perf_counter()
        for item in annotations["images"]:
            tensor, transform = letterbox(args.dataset / "images" / item["file_name"])
            started = time.perf_counter(); outputs = rknn.inference(inputs=[tensor]); timings.append(time.perf_counter() - started)
            boxes, scores, classes = boxes_from_outputs(outputs, args.threshold)
            scale, left, top, width, height = transform
            for index in nms(boxes, scores, classes):
                box = boxes[index].copy(); box[[0, 2]] = np.clip((box[[0, 2]] - left) / scale, 0, width); box[[1, 3]] = np.clip((box[[1, 3]] - top) / scale, 0, height)
                predictions.append({"image_id": item["id"], "category_id": COCO_IDS[int(classes[index])], "bbox": [round(float(box[0]), 3), round(float(box[1]), 3), round(float(box[2] - box[0]), 3), round(float(box[3] - box[1]), 3)], "score": round(float(scores[index]), 6)})
        elapsed = time.perf_counter() - overall_start
    finally: rknn.release()
    (args.dataset / f"predictions-{args.profile}.json").write_text(json.dumps(predictions))
    measured = timings[min(10, len(timings)):]
    (args.dataset / f"benchmark-{args.profile}.json").write_text(json.dumps({"profile": args.profile, "images": len(annotations["images"]), "detections": len(predictions), "pipeline_fps": len(annotations["images"]) / elapsed, "inference_fps": len(measured) / sum(measured), "warmup_images": min(10, len(timings))}))
    print(json.dumps(json.loads((args.dataset / f"benchmark-{args.profile}.json").read_text()), indent=2))


if __name__ == "__main__": main()
