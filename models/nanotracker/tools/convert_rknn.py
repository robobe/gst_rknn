#!/usr/bin/env python3
"""Build NanoTrackV3 mixed or fully INT8 RKNN models with RKNN Toolkit 2."""

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
    parser.add_argument("--profile", choices=("mixed", "int8", "int8-mmse"), default="mixed")
    args = parser.parse_args()

    template = ONNX / "nanotrack_backbone_template.onnx"
    backbone = ONNX / "nanotrack_backbone.onnx"
    head = ONNX / "nanotrack_head.onnx"
    for source in (template, backbone, head):
        if not source.is_file():
            parser.error(f"missing {source}")

    OUTPUT.mkdir(exist_ok=True)
    calibration = ROOT / "tools" / "calibration"
    head_dataset, template_dataset, search_dataset = (calibration / item for item in ("dataset.txt", "template_images.txt", "search_images.txt"))
    if not head_dataset.is_file(): parser.error("run generate_calibration.py first")
    if args.profile == "mixed":
        convert(template, OUTPUT / "nanotrack_backbone_template.rknn")
        convert(backbone, OUTPUT / "nanotrack_backbone.rknn")
        convert(head, OUTPUT / "nanotrack_head_int8.rknn", True, head_dataset)
        return
    if not template_dataset.is_file() or not search_dataset.is_file(): parser.error("run generate_calibration.py again to create image lists")
    suffix, algorithm = ("_int8_mmse", "mmse") if args.profile == "int8-mmse" else ("_int8", "normal")
    convert(template, OUTPUT / f"nanotrack_backbone_template{suffix}.rknn", True, template_dataset, algorithm)
    convert(backbone, OUTPUT / f"nanotrack_backbone{suffix}.rknn", True, search_dataset, algorithm)
    convert(head, OUTPUT / f"nanotrack_head{suffix}.rknn", True, head_dataset, algorithm)


if __name__ == "__main__":
    main()
