#!/usr/bin/env python3
"""Convert NanoTrackV3 ONNX models with RKNN Toolkit 2."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ONNX = ROOT / "onnx"
OUTPUT = ROOT / "rknn"


def convert(onnx_path, output_path, quantize=False, dataset=None, algorithm="normal"):
    from rknn.api import RKNN

    rknn = RKNN(verbose=False)
    try:
        config = {"target_platform": "rk3566", "optimization_level": 3}
        if quantize:
            config.update(quantized_dtype="asymmetric_quantized-8",
                          quantized_method="channel", quantized_algorithm=algorithm)
        assert rknn.config(**config) == 0, "rknn.config failed"
        assert rknn.load_onnx(model=str(onnx_path)) == 0, f"cannot load {onnx_path}"
        assert rknn.build(do_quantization=quantize, dataset=str(dataset) if dataset else None) == 0, "rknn.build failed"
        assert rknn.export_rknn(str(output_path)) == 0, f"cannot export {output_path}"
    finally:
        rknn.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head-dataset", type=Path,
                        help="Representative head-feature dataset list; required for INT8 head conversion")
    parser.add_argument("--quant-algorithm", choices=("normal", "mmse"), default="normal")
    parser.add_argument("--skip-head", action="store_true")
    args = parser.parse_args()

    template = ONNX / "nanotrack_backbone_template.onnx"
    backbone = ONNX / "nanotrack_backbone.onnx"
    head = ONNX / "nanotrack_head.onnx"
    for source in (template, backbone, head):
        if not source.is_file():
            parser.error(f"missing {source}")

    OUTPUT.mkdir(exist_ok=True)
    convert(template, OUTPUT / "nanotrack_backbone_template.rknn")
    convert(backbone, OUTPUT / "nanotrack_backbone.rknn")
    if not args.skip_head:
        if not args.head_dataset or not args.head_dataset.is_file():
            parser.error("--head-dataset is required unless --skip-head is used")
        convert(head, OUTPUT / "nanotrack_head_int8.rknn", True, args.head_dataset, args.quant_algorithm)


if __name__ == "__main__":
    main()
