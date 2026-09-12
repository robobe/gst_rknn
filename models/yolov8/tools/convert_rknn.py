#!/usr/bin/env python3
"""Convert a fixed-shape YOLOv8 ONNX model to an INT8 RKNN model."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", type=Path, default=ROOT / "onnx" / "yolov8n.onnx")
    parser.add_argument("--dataset", type=Path, required=True,
                        help="text file containing representative calibration-image paths")
    parser.add_argument("--output", type=Path, default=ROOT / "rknn" / "yolov8n-rk3566-int8.rknn")
    parser.add_argument("--target", default="rk3566")
    args = parser.parse_args()

    for path in (args.onnx, args.dataset):
        if not path.is_file():
            parser.error(f"missing {path}")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    from rknn.api import RKNN

    rknn = RKNN(verbose=False)
    try:
        assert rknn.config(mean_values=[[0, 0, 0]], std_values=[[255, 255, 255]],
                           target_platform=args.target) == 0, "rknn.config failed"
        assert rknn.load_onnx(model=str(args.onnx)) == 0, f"cannot load {args.onnx}"
        assert rknn.build(do_quantization=True, dataset=str(args.dataset)) == 0, "INT8 build failed"
        assert rknn.export_rknn(str(args.output)) == 0, f"cannot write {args.output}"
    finally:
        rknn.release()
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
