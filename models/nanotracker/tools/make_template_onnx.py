#!/usr/bin/env python3
"""Derive the 127x127 NanoTrack template backbone ONNX without changing weights."""

from pathlib import Path

import onnx


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "onnx" / "nanotrack_backbone.onnx"
output = ROOT / "onnx" / "nanotrack_backbone_template.onnx"

model = onnx.load(source)
input_shape = model.graph.input[0].type.tensor_type.shape.dim
input_shape[2].dim_value = 127
input_shape[3].dim_value = 127
for value in model.graph.output:
    shape = value.type.tensor_type.shape.dim
    shape[2].dim_value = 8
    shape[3].dim_value = 8
model = onnx.shape_inference.infer_shapes(model)
onnx.checker.check_model(model)
onnx.save(model, output)
print(output)
