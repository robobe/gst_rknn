#!/usr/bin/env python3
"""Run RKNN YOLOv8 on the Model Zoo bus image and compare reference detections."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from rknnlite.api import RKNNLite


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (
    ("person", (211, 241, 283, 507), 0.873),
    ("person", (109, 235, 225, 536), 0.866),
    ("person", (476, 222, 560, 521), 0.863),
    ("bus", (99, 136, 550, 456), 0.859),
    ("person", (80, 326, 116, 513), 0.311),
)
CLASSES = ("person", "bicycle", "car", "motorcycle", "airplane", "bus")


def boxes_from_outputs(outputs, threshold=0.2):
    boxes, scores, classes = [], [], []
    for position, confidence, _ in zip(outputs[::3], outputs[1::3], outputs[2::3]):
        _, _, height, width = position.shape
        distance = position.reshape(1, 4, 16, height, width)
        distance = np.exp(distance - distance.max(axis=2, keepdims=True))
        distance = (distance / distance.sum(axis=2, keepdims=True) * np.arange(16).reshape(1, 1, 16, 1, 1)).sum(axis=2)
        col, row = np.meshgrid(np.arange(width), np.arange(height))
        grid = np.stack((col, row), axis=0).reshape(1, 2, height, width)
        stride = 640 // width
        xyxy = np.concatenate((grid + .5 - distance[:, :2], grid + .5 + distance[:, 2:]), axis=1) * stride
        confidence = confidence.transpose(0, 2, 3, 1).reshape(-1, confidence.shape[1])
        xyxy = xyxy.transpose(0, 2, 3, 1).reshape(-1, 4)
        label = confidence.argmax(axis=1)
        score = confidence.max(axis=1)
        keep = score >= threshold
        boxes.extend(xyxy[keep])
        scores.extend(score[keep])
        classes.extend(label[keep])
    return np.asarray(boxes), np.asarray(scores), np.asarray(classes)


def iou(first, second):
    left, top = np.maximum(first[:2], second[:2])
    right, bottom = np.minimum(first[2:], second[2:])
    overlap = max(0, right - left) * max(0, bottom - top)
    return overlap / (max(0, first[2] - first[0]) * max(0, first[3] - first[1]) + max(0, second[2] - second[0]) * max(0, second[3] - second[1]) - overlap)


def compare(boxes, scores, classes):
    failures = []
    for name, expected_box, expected_score in REFERENCE:
        class_id = CLASSES.index(name)
        candidates = np.where(classes == class_id)[0]
        if not len(candidates):
            failures.append(f"missing {name} {expected_box}")
            continue
        index = max(candidates, key=lambda item: iou(boxes[item], expected_box))
        overlap = iou(boxes[index], expected_box)
        score_delta = abs(scores[index] - expected_score)
        print(f"{name}: box={np.rint(boxes[index]).astype(int).tolist()} score={scores[index]:.3f} iou={overlap:.3f} score_delta={score_delta:.3f}")
        if overlap < .80 or score_delta > .15:
            failures.append(f"{name}: iou={overlap:.3f}, score_delta={score_delta:.3f}")
    assert not failures, "reference comparison failed: " + "; ".join(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=ROOT / "rknn" / "yolov8n-rk3566-int8.rknn")
    parser.add_argument("--image", type=Path, default=ROOT / "testdata" / "bus.jpg")
    args = parser.parse_args()
    for path in (args.model, args.image):
        if not path.is_file(): parser.error(f"missing {path}")
    image = np.asarray(Image.open(args.image).convert("RGB"))
    if image.shape != (640, 640, 3): parser.error(f"expected 640x640 image, got {image.shape}")

    rknn = RKNNLite(verbose=False)
    try:
        assert rknn.load_rknn(str(args.model)) == 0, "load_rknn failed"
        assert rknn.init_runtime() == 0, "init_runtime failed"
        outputs = rknn.inference(inputs=[image[None]])
        assert outputs, "inference returned no outputs"
        print("smoke test passed:", ", ".join(str(output.shape) for output in outputs))
        boxes, scores, classes = boxes_from_outputs(outputs)
        compare(boxes, scores, classes)
    finally:
        rknn.release()


if __name__ == "__main__":
    main()
