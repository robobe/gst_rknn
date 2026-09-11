# Remote scripts

All scripts use `radxa@radxa` and `/home/radxa/gst-rknn` by default. Override
them with `RADXA_HOST`, `RADXA_USER`, and `RADXA_ROOT`.

| Command | Purpose |
| --- | --- |
| `./scripts/deploy.sh plugin` | Deploy all built `.so` modules and `plugin_list.md`. |
| `./scripts/deploy.sh models` | Deploy model directories. |
| `./scripts/deploy.sh assets` | Deploy generated videos, ground truth, and the comparator. |
| `./scripts/deploy.sh all` | Deploy plugins, models, and assets. |
| `./scripts/remote-test.sh inspect` | Inspect the `rknnhello` plugin. |
| `./scripts/remote-test.sh smoke` | Run the one-frame hello pipeline. |
| `./scripts/nanotracker/test.sh inspect` | Inspect `rknnnanotrack`. |
| `./scripts/nanotracker/test.sh smoke` | Run 60 generated BGR frames through NanoTracker. |
| `./scripts/nanotracker/test.sh video` | Run the 500-frame MP4; writes `predictions.csv`, `run_metrics.txt`, and `run_pipeline.txt` under remote NanoTracker assets. |
| `./scripts/nanotracker/test.sh compare` | Compare predictions to ground truth and print IoU, FPS, and the pipeline command. |
| `./scripts/nanotracker/stream.sh` | Stream NanoTracker H.264/RTP video and ROI metadata to `video-metadata-viewer`. |
| `./scripts/nanotracker12/test.sh inspect` | Inspect the independent NanoTrack V1/V2 element. |
| `./scripts/nanotracker12/test.sh smoke v1\|v2` | Run 60 BGR frames through the selected V1 or V2 model. |
| `./scripts/nanotracker12/test.sh video v1\|v2` | Write selected-version tracking metadata for the 500-frame synthetic video. |
| `./scripts/nanotracker12/stream-v1.sh` | Stream V1 H.264/RTP video and `nanotrack` metadata to the host viewer. |
| `./scripts/nanotracker12/stream-v2.sh` | Stream V2 H.264/RTP video and `nanotrack` metadata to the host viewer. |
