#!/usr/bin/env python3
"""Build a reviewed FP16-output / INT8 YOLOv8 RKNN model in two steps."""

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(result, operation):
    assert result == 0, f"{operation} failed with return code {result}"


def add_fp16_layers(config, layers):
    text = config.read_text()
    marker = "custom_quantize_layers: {}"
    assert marker in text, f"{config} has already been edited; review it and rerun without --fp16-layer"
    entries = "\n".join(f"  {layer!r}: float16" for layer in layers)
    config.write_text(text.replace(marker, f"custom_quantize_layers:\n{entries}", 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("step1", "step2"))
    parser.add_argument("--onnx", type=Path, default=ROOT / "onnx" / "yolov8n.onnx")
    parser.add_argument("--dataset", type=Path, default=ROOT.parents[1] / "assets" / "coco_train_sample" / "calibration.txt")
    parser.add_argument("--workdir", type=Path, default=ROOT / "hybrid-work")
    parser.add_argument("--output", type=Path, default=ROOT / "rknn" / "yolov8n-rk3566-hybrid-int8.rknn")
    parser.add_argument("--target", default="rk3566")
    parser.add_argument("--fp16-layer", action="append", default=[], help="reviewed Step 1 tensor name; repeat for each FP16 tensor")
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    stem = args.onnx.stem
    model, data, config = (args.workdir / f"{stem}{suffix}" for suffix in (".model", ".data", ".quantization.cfg"))

    if args.phase == "step1":
        for path in (args.onnx, args.dataset):
            if not path.is_file(): parser.error(f"missing {path}")
        from rknn.api import RKNN
        os.chdir(args.workdir)
        rknn = RKNN(verbose=False)
        try:
            require(rknn.config(mean_values=[[0, 0, 0]], std_values=[[255, 255, 255]], target_platform=args.target), "config")
            require(rknn.load_onnx(model=str(args.onnx.resolve())), "load_onnx")
            require(rknn.hybrid_quantization_step1(dataset=str(args.dataset.resolve()), proposal=False), "hybrid_quantization_step1")
        finally:
            rknn.release()
        assert all(path.is_file() for path in (model, data, config)), f"Step 1 artifacts missing from {args.workdir}"
        print(f"review {config}; then run step2 with one --fp16-layer per detection-output tensor")
        return

    for path in (model, data, config):
        if not path.is_file(): parser.error(f"missing Step 1 artifact {path}")
    if args.fp16_layer:
        add_fp16_layers(config, args.fp16_layer)
    assert "float16" in config.read_text(), "Step 2 requires reviewed FP16 detection-output tensors via --fp16-layer"
    from rknn.api import RKNN
    rknn = RKNN(verbose=False)
    try:
        require(rknn.hybrid_quantization_step2(str(model), str(data), str(config)), "hybrid_quantization_step2")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        require(rknn.export_rknn(str(args.output)), "export_rknn")
    finally:
        rknn.release()
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
