# YOLOv8 model assets

This directory holds the RK3566 INT8 YOLOv8 model used by the future GStreamer
plugin. Keep source models in `onnx/` and generated board artifacts in `rknn/`.
Neither is committed.

## Convert on the x86_64 development host

Use the RKNN Toolkit2 release matching the board's RKNN runtime. Download the
Rockchip-optimized `yolov8n.onnx` to `onnx/`, then make `calibration.txt` with
one representative camera-image path per line:

```sh
./scripts/ensure-rknn-toolkit.sh
.venv-rknn/bin/python models/yolov8/tools/convert_rknn.py \
  --dataset /path/to/calibration.txt
```

The model expects a batched `1x640x640x3` RGB HWC `uint8` input. The converter applies the
model's `/255` normalization.

## Smoke test on the Radxa Zero 3W

```sh
python3 -m pip install --user --break-system-packages pillow
./scripts/deploy.sh models
ssh radxa@radxa 'python3 /home/radxa/gst-rknn/models/yolov8/tools/smoke_test.py'
```

The smoke test uses `rknn-toolkit-lite2` on the board, loads the model, runs
the bundled Model Zoo `testdata/bus.jpg`, and compares its detections against
Rockchip's published reference results. It is a regression check, not ground
truth or an accuracy evaluation.

## Reproducible COCO accuracy and FPS sample

Create the fixed 200-image COCO val2017 subset, deploy it, then run evaluation
on the board and render the host-side report:

```sh
.venv-rknn/bin/python tools/fetch_coco_val_sample.py
./scripts/deploy.sh assets
./scripts/deploy.sh models
ssh radxa@radxa 'python3 /home/radxa/gst-rknn/models/yolov8/tools/benchmark_coco.py --profile int8 --dataset /home/radxa/gst-rknn/assets/coco_val_sample'
rsync -a radxa@radxa:/home/radxa/gst-rknn/assets/coco_val_sample/{predictions,benchmark}-int8.json assets/coco_val_sample/
uv pip install --python .venv-rknn/bin/python pycocotools
.venv-rknn/bin/python tools/report_yolo_coco.py
```

The images, annotations, detections, and timing JSON remain local under
`assets/coco_val_sample/`; the generated comparison record is
[`docs/guides/yolov8-coco-val-sample.md`](../../docs/guides/yolov8-coco-val-sample.md).

## Hybrid-INT8 conversion with Toolkit2 2.3.2

Hybrid conversion keeps only verified detection-output tensors in FP16 and
quantizes the rest to INT8. It is a two-step review process: Step 1 creates
the Toolkit configuration, and Step 2 builds only after the reviewed tensor
names are provided. Do not reuse the validation sample for calibration.

```sh
./scripts/ensure-rknn-toolkit.sh
.venv-rknn/bin/python tools/fetch_coco_val_sample.py --split train
.venv-rknn/bin/python models/yolov8/tools/fetch_yolov8n_onnx.py
.venv-rknn/bin/python models/yolov8/tools/convert_hybrid_rknn.py step1
sed -n '1,80p' models/yolov8/hybrid-work/yolov8n.quantization.cfg
# Copy the generated detection-output tensor names from custom_quantize_layers.
.venv-rknn/bin/python models/yolov8/tools/convert_hybrid_rknn.py step2 \\
  --fp16-layer <reviewed-output-tensor> --fp16-layer <reviewed-output-tensor>
bash scripts/yolov8/hybrid-evaluate.sh
```

`hybrid-evaluate.sh` deploys both artifacts, runs both Model Zoo smoke tests
and the same COCO validation benchmark, then writes
[`docs/guides/yolov8-hybrid-int8-comparison.md`](../../docs/guides/yolov8-hybrid-int8-comparison.md).
The complete procedure is in
[`docs/guides/yolov8-hybrid-int8-conversion.md`](../../docs/guides/yolov8-hybrid-int8-conversion.md).
The source ONNX URL and checksum are pinned by the fetch helper. The approach
follows the [two-step FP16-output hybrid method](https://github.com/mahdieh-jokar/yolo26n-rknn-int8-quantization/blob/main/README.md), but uses the names Toolkit generates for this YOLOv8 graph.
