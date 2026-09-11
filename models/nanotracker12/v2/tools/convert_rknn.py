#!/usr/bin/env python3
"""Build NanoTrack V2 mixed or fully INT8 RKNN models for RK3566."""
import argparse
from pathlib import Path
from rknn.api import RKNN

ROOT = Path(__file__).resolve().parents[1]

def build(source, target, quantize=False, dataset=None, algorithm="normal"):
    rknn = RKNN(verbose=False)
    try:
        rknn.config(target_platform="rk3566", optimization_level=3, quantized_algorithm=algorithm)
        if rknn.load_onnx(model=str(source)) != 0: raise RuntimeError(f"load failed: {source}")
        if rknn.build(do_quantization=quantize, dataset=str(dataset) if dataset else None) != 0: raise RuntimeError(f"build failed: {source}")
        if rknn.export_rknn(str(target)) != 0: raise RuntimeError(f"export failed: {target}")
    finally: rknn.release()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--profile", choices=("mixed", "int8", "int8-mmse"), default="mixed"); args = parser.parse_args()
    out = ROOT / "rknn"; out.mkdir(exist_ok=True); onnx = ROOT / "onnx"; calibration = ROOT / "tools/calibration"
    head_dataset, template_dataset, search_dataset = (calibration / item for item in ("dataset.txt", "template_images.txt", "search_images.txt"))
    if not head_dataset.exists(): raise SystemExit("run generate_calibration.py first")
    if args.profile == "mixed":
        build(onnx / "nanotrack_backbone_template_sim.onnx", out / "nanotrack_backbone_template.rknn")
        build(onnx / "nanotrack_backbone_sim.onnx", out / "nanotrack_backbone.rknn")
        build(onnx / "nanotrack_head_sim.onnx", out / "nanotrack_head_int8.rknn", True, head_dataset)
        return
    if not template_dataset.exists() or not search_dataset.exists(): raise SystemExit("run generate_calibration.py again to create image lists")
    suffix, algorithm = ("_int8_mmse", "mmse") if args.profile == "int8-mmse" else ("_int8", "normal")
    build(onnx / "nanotrack_backbone_template_sim.onnx", out / f"nanotrack_backbone_template{suffix}.rknn", True, template_dataset, algorithm)
    build(onnx / "nanotrack_backbone_sim.onnx", out / f"nanotrack_backbone{suffix}.rknn", True, search_dataset, algorithm)
    build(onnx / "nanotrack_head_sim.onnx", out / f"nanotrack_head{suffix}.rknn", True, head_dataset, algorithm)

if __name__ == "__main__": main()
