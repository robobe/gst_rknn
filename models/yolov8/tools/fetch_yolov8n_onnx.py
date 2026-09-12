#!/usr/bin/env python3
"""Fetch the pinned Rockchip-optimized YOLOv8n ONNX model."""

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parents[1]
URL = "https://ftrg.zbox.filez.com/v2/delivery/data/95f00b0fc900458ba134f8b180b3f7a1/examples/yolov8/yolov8n.onnx"
SHA256 = "0c8716701f471067932b797eeb67c8e5db47c693c2557c881d7679ec12e21bc5"
MODEL_ZOO_COMMIT = "bad6c7334531becaf90a561988519b7bec34d0ab"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "onnx" / "yolov8n.onnx")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not args.output.is_file() or digest(args.output) != SHA256:
        print(f"downloading Model Zoo commit {MODEL_ZOO_COMMIT}")
        urlretrieve(URL, args.output)
    actual = digest(args.output)
    assert actual == SHA256, f"SHA-256 mismatch: {actual}"
    print(f"verified {args.output}: {actual}")


if __name__ == "__main__":
    main()
