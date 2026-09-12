# Metadata-paced RKNN benchmark application

The Radxa server runs one selected NanoTrack V1/V2/V3 or YOLOv8n pipeline at a time and sends
metadata only on UDP 5005. The desktop client selects its local mirrored dataset root, browses
`/home/radxa/gst-rknn/datasets`, and derives the local source path from the same relative path.
It decodes the local source, selects an initial ROI only for trackers, and waits for each metadata
frame before displaying it.

Use **Show pipeline** during or after a run to view and copy the exact `gst-launch-1.0`
command saved with that run. The server ends each inference pipeline at a synced
`fakesink`; no video bytes are sent over the network.

The client stores the last ten successful run configurations plus named presets
in `~/.config/gst-rknn/nanotracker-benchmark-last-run.yaml`. Select one from the
scrollable recent/preset list to reload it; enter a preset name and choose
**Save** to retain the current form, or **Rename** to rename the selected preset.
The selected client dataset root is retained with each saved selection.

Use **Play source** to play the selected mirrored file or image sequence locally
without contacting the Radxa server.

Pipeline profiles live in `server.yaml`. Each profile specifies its GStreamer
element, required input format, whether it needs a selected ROI, and its fixed
element properties. This keeps model paths and benchmark variants out of Python.
The YOLOv8n INT8 profile is the normal choice; hybrid-INT8 remains selectable for
comparison. YOLO receives RGB input, does not need an ROI, emits every detection
with COCO class ID and confidence, and disables NanoTracker CSV ground truth/IoU
scoring. Its summary reports detections per second and client FPS instead.

`roi2udp` writes `pts_ns,roi_type,x,y,width,height,initialized,confidence,class_id,frame_id`.
Each buffer ends with a `roi_type=frame` marker, including zero-detection frames. The client
uses the monotonic frame ID and PTS to synchronize its local decoder; after 500 ms without a
marker it advances without boxes and marks metadata loss instead of freezing.

```bash
./scripts/deploy.sh all
./scripts/deploy.sh benchmark
./scripts/deploy.sh benchmark-setup  # installs app-local uv and server environment
./scripts/nanotracker-benchmark-server.sh
```

Copy the development host's dataset collection when needed:

```bash
./scripts/deploy.sh datasets
```

The server browser opens at `/home/radxa/gst-rknn/datasets` by default.

On the development host, update `client.yaml` when its metadata receiving LAN IP changes,
then run `python3 apps/nanotracker_benchmark/client.py`.

The desktop client uses the same system packages as the existing Python viewer:
PyGObject/GStreamer, OpenCV, NumPy, and PyYAML. The Radxa setup installs an
application-local `uv` binary and creates `.venv` with system PyGObject access
without modifying Ubuntu's managed Python.

Each Radxa run is saved under `/home/radxa/gst-rknn/benchmarks/<run-id>/` with
the request, exact pipeline, log, prediction CSV, JSON summary, and IoU report
when the dataset has ground truth. Server and client FPS are intentionally
separate from tracker-only `fakesink` benchmarks.
