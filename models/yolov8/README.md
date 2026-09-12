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
ssh radxa@radxa 'python3 /home/radxa/gst-rknn/models/yolov8/tools/benchmark_coco.py --dataset /home/radxa/gst-rknn/assets/coco_val_sample'
rsync -a radxa@radxa:/home/radxa/gst-rknn/assets/coco_val_sample/{predictions,benchmark}.json assets/coco_val_sample/
uv pip install --python .venv-rknn/bin/python pycocotools
.venv-rknn/bin/python tools/report_yolo_coco.py
```

The images, annotations, detections, and timing JSON remain local under
`assets/coco_val_sample/`; the generated comparison record is
[`docs/guides/yolov8-coco-val-sample.md`](../../docs/guides/yolov8-coco-val-sample.md).
