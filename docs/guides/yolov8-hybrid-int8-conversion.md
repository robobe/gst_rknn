# YOLOv8n RK3566 hybrid-INT8 conversion

This profile uses RKNN Toolkit2 2.3.2 mixed precision: all supported layers
remain INT8 except the nine verified detection-output tensors, retained as
FP16. This follows the [two-step hybrid method](https://github.com/mahdieh-jokar/yolo26n-rknn-int8-quantization/blob/main/README.md), but the tensor names are generated from the Rockchip-optimized YOLOv8 graph rather than copied from another YOLO variant.

## Build

```sh
./scripts/ensure-rknn-toolkit.sh
.venv-rknn/bin/python tools/fetch_coco_val_sample.py --split train
.venv-rknn/bin/python models/yolov8/tools/fetch_yolov8n_onnx.py
.venv-rknn/bin/python models/yolov8/tools/convert_hybrid_rknn.py step1
.venv-rknn/bin/python models/yolov8/tools/convert_hybrid_rknn.py step2 \
  --fp16-layer 318 --fp16-layer onnx::ReduceSum_326 --fp16-layer 331 \
  --fp16-layer 338 --fp16-layer onnx::ReduceSum_346 --fp16-layer 350 \
  --fp16-layer 357 --fp16-layer onnx::ReduceSum_365 --fp16-layer 369
```

Step 1 writes `models/yolov8/hybrid-work/yolov8n.quantization.cfg`, `.model`,
and `.data`. Review the config before Step 2. Numeric tensor names must be
quoted in YAML; `convert_hybrid_rknn.py` does this automatically when passed
through `--fp16-layer`.

The ONNX fetcher pins the Model Zoo source commit
`bad6c7334531becaf90a561988519b7bec34d0ab` and SHA-256
`0c8716701f471067932b797eeb67c8e5db47c693c2557c881d7679ec12e21bc5`.
The separate 200-image COCO train2017 set calibrates quantization; do not use
the COCO val2017 sample for calibration.

## Deploy and compare

```sh
bash scripts/yolov8/hybrid-evaluate.sh
```

This deploys both models, runs their `bus.jpg` smoke checks and the same
200-image COCO val2017 evaluation, then creates
[the comparison record](yolov8-hybrid-int8-comparison.md). It recommends
hybrid-INT8 only when mAP50:95 improves and inference remains at least 85% of
the calibrated INT8 baseline.
