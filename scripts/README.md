# Remote scripts

All scripts use `radxa@radxa` and `/home/radxa/gst-rknn` by default. Override
them with `RADXA_HOST`, `RADXA_USER`, and `RADXA_ROOT`.

| Command | Purpose |
| --- | --- |
| `./scripts/deploy.sh plugin` | Deploy all built `.so` modules and `plugin_list.md`. |
| `./scripts/deploy.sh models` | Deploy model directories. |
| `./scripts/deploy.sh assets` | Deploy generated videos, ground truth, and the comparator. |
| `./scripts/deploy.sh datasets` | Rsync `/home/user/datasets/` to `/home/radxa/gst-rknn/datasets/`; override the source with `DATASETS_DIR`. It never deletes remote files. |
| `./scripts/deploy.sh benchmark` | Deploy the NanoTracker benchmark application source. |
| `./scripts/deploy.sh benchmark-setup` | Deploy the benchmark source and create/update its Radxa Python venv. |
| `./scripts/deploy.sh all` | Deploy plugins, models, and assets. |
| `./scripts/ensure-rknn-toolkit.sh` | Create/update the host Python 3.12 `uv` environment with RKNN-Toolkit2 2.3.2. |
| `bash ./scripts/yolov8/hybrid-evaluate.sh` | Deploy and smoke-test the INT8 and hybrid-INT8 YOLOv8 models, evaluate both on COCO val, and write their comparison report. |
| `bash ./scripts/yolov8/test-plugin.sh` | Cross-build, deploy, inspect, and smoke-test the RGB YOLOv8 detection plugin. |
| Planned `bash ./scripts/yolov8/benchmark-camera.sh` | Measure the camera-equivalent YOLO detector path; see [`yolov8-camera-detector-benchmark.md`](../docs/guides/yolov8-camera-detector-benchmark.md) for its timing boundary and quality metric. |
| `sudo ./scripts/install-rknn-runtime-2.3.2.sh` | Install the staged RKNN 2.3.2 board runtime and save a system backup. |
| `./scripts/remote-test.sh inspect` | Inspect the `rknnhello` plugin. |
| `./scripts/remote-test.sh smoke` | Run the one-frame hello pipeline. |
| `./scripts/nanotracker/test.sh inspect` | Inspect `rknnnanotrack`. |
| `./scripts/nanotracker/test.sh smoke` | Run 60 generated BGR frames through NanoTracker. |
| `./scripts/nanotracker/test.sh video` | Run the 500-frame MP4; writes `predictions.csv`, `run_metrics.txt`, and `run_pipeline.txt` under remote NanoTracker assets. |
| `./scripts/nanotracker/test.sh compare` | Compare predictions to ground truth and print IoU, FPS, and the pipeline command. |
| `./scripts/nanotracker/test.sh bench` | Run five V3 INT8 RGA/fakesink passes and print post-warm-up median FPS; set `NANOTRACK_PRECISION=mixed` or `int8-mmse` to compare. |
| `./scripts/nanotracker/test.sh matrix` | Compare deployed V3 `mixed`, `int8`, and `int8-mmse` profiles on the 500-frame video; writes the guide's CSV, SVG, and results table. |
| `./scripts/nanotracker/stream.sh` | Stream NanoTracker H.264/RTP video and ROI metadata to `video-metadata-viewer`. |
| `./scripts/nanotracker-benchmark-server.sh` | Run the Radxa FastAPI NanoTracker benchmark server. |
| `./scripts/nanotracker12/test.sh inspect` | Inspect the independent NanoTrack V1/V2 element. |
| `./scripts/nanotracker12/test.sh smoke v1\|v2` | Run 60 BGR frames through the selected V1 or V2 model. |
| `./scripts/nanotracker12/test.sh video v1\|v2` | Write selected-version tracking metadata for the 500-frame synthetic video. |
| `./scripts/nanotracker12/test.sh bench v2` | Run five V2 INT8 fakesink passes and print the post-warm-up median FPS; use `NANOTRACK_PRECISION=mixed` to compare mixed. |
| `./scripts/nanotracker12/stream-v1.sh` | Stream V1 H.264/RTP video and `nanotrack` metadata to the host viewer. |
| `./scripts/nanotracker12/stream-v2.sh` | Stream V2 H.264/RTP video and `nanotrack` metadata to the host viewer. |
