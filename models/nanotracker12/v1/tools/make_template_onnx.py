#!/usr/bin/env python3
"""Derive the 127x127 template backbone ONNX from the upstream 255x255 export."""
from pathlib import Path
import onnx

root = Path(__file__).resolve().parents[1]
source = root / "onnx/nanotrack_backbone_sim.onnx"
target = root / "onnx/nanotrack_backbone_template_sim.onnx"
model = onnx.load(source)
for value in (model.graph.input[0], model.graph.output[0]):
    dims = value.type.tensor_type.shape.dim
    dims[2].dim_value = 127 if value is model.graph.input[0] else 8
    dims[3].dim_value = 127 if value is model.graph.input[0] else 8
# V1's export stores stale fixed intermediate shapes; they are not graph inputs.
del model.graph.value_info[:]
onnx.save(model, target)
print(target)
