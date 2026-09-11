#!/usr/bin/env python3
"""Create NanoTrackV3 image and head-feature calibration data from synthetic GT."""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path(__file__).resolve().parents[3]

def crop(frame, box, output):
    x, y, width, height = box
    side = round(np.sqrt((width + .5 * (width + height)) * (height + .5 * (width + height))))
    if output == 255: side = round(side * 255 / 127)
    center_x, center_y = x + (width - 1) / 2, y + (height - 1) / 2
    left, top = int(np.floor(center_x - side / 2)), int(np.floor(center_y - side / 2))
    padded = np.full((side, side, 3), frame.mean(axis=(0, 1)), dtype=np.uint8)
    x0, y0, x1, y1 = max(0, left), max(0, top), min(frame.shape[1], left + side), min(frame.shape[0], top + side)
    if x1 > x0 and y1 > y0: padded[y0 - top:y1 - top, x0 - left:x1 - left] = frame[y0:y1, x0:x1]
    return cv2.resize(padded, (output, output), interpolation=cv2.INTER_LINEAR)

def run(session, image):
    tensor = image.transpose(2, 0, 1)[None].astype(np.float32)
    return session.run(None, {session.get_inputs()[0].name: tensor})[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, default=PROJECT / "assets/nanotracker/move_right_500.mp4")
    parser.add_argument("--ground-truth", type=Path, default=PROJECT / "assets/nanotracker/move_right_500.csv")
    parser.add_argument("--max-samples", type=int, default=128)
    args = parser.parse_args()
    out = ROOT / "tools/calibration"; out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(args.ground_truth.open()))
    capture = cv2.VideoCapture(str(args.video)); ok, template_frame = capture.read()
    if not ok: raise SystemExit(f"cannot read {args.video}")
    backbone = ort.InferenceSession(str(ROOT / "onnx/nanotrack_backbone.onnx"), providers=["CPUExecutionProvider"])
    template = ort.InferenceSession(str(ROOT / "onnx/nanotrack_backbone_template.onnx"), providers=["CPUExecutionProvider"])
    template_box = [float(rows[0][key]) for key in ("x", "y", "width", "height")]
    template_image = crop(template_frame, template_box, 127); template_feature = run(template, template_image)
    pairs, template_images, search_images = [], [], []
    for index, row in enumerate(rows[:args.max_samples]):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index); ok, frame = capture.read()
        if not ok: break
        box = [float(row[key]) for key in ("x", "y", "width", "height")]
        search_image = crop(frame, box, 255)
        first, second = out / f"template_{index:03d}.npy", out / f"search_{index:03d}.npy"
        np.save(first, template_feature); np.save(second, run(backbone, search_image)); pairs.append(f"{first} {second}")
        template_png, search_png = out / f"template_{index:03d}.png", out / f"search_{index:03d}.png"
        if not cv2.imwrite(str(template_png), template_image) or not cv2.imwrite(str(search_png), search_image): raise SystemExit("cannot write calibration image")
        template_images.append(str(template_png)); search_images.append(str(search_png))
    (out / "dataset.txt").write_text("\n".join(pairs) + "\n")
    (out / "template_images.txt").write_text("\n".join(template_images) + "\n")
    (out / "search_images.txt").write_text("\n".join(search_images) + "\n")
    print(f"wrote {len(pairs)} V3 calibration samples to {out}")

if __name__ == "__main__": main()
