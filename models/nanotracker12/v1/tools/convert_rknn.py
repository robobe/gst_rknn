#!/usr/bin/env python3
"""Build NanoTrack V1 RKNN models for RK3566 with the mixed default set."""
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
    parser = argparse.ArgumentParser(); parser.add_argument("--head-algorithm", choices=("normal", "mmse"), default="normal"); args = parser.parse_args()
    out = ROOT / "rknn"; out.mkdir(exist_ok=True); onnx = ROOT / "onnx"; dataset = ROOT / "tools/calibration/dataset.txt"
    if not dataset.exists(): raise SystemExit("run generate_calibration.py first")
    build(onnx / "nanotrack_backbone_template_sim.onnx", out / "nanotrack_backbone_template.rknn")
    build(onnx / "nanotrack_backbone_sim.onnx", out / "nanotrack_backbone.rknn")
    build(onnx / "nanotrack_head_sim.onnx", out / "nanotrack_head_int8.rknn", True, dataset, args.head_algorithm)

if __name__ == "__main__": main()
