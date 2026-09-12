# NanoTracker benchmark application

The Radxa server runs one selected NanoTrack V1/V2/V3 pipeline at a time and
streams resized 640×360 MJPEG/RTP video on UDP 5004 plus ROI metadata on UDP 5005. The desktop
client browses `/home/radxa`, previews a source frame, selects the initial ROI,
and displays the result. Its server LED is green when the FastAPI health check
is reachable and red when the server cannot be contacted.

Use **Show pipeline** during or after a run to view and copy the exact `gst-launch-1.0`
command saved with that run. Video is resized before tracking and sent as JPEG
frames at quality 85, so every received frame is independently decodable.

The sender follows source timestamps and the receiver keeps a 200-ms RTP jitter
buffer. This prevents Wi-Fi bursts from dropping frames; it adds about 200 ms of
intentional display latency for smooth playback.

The client stores the last ten successful run configurations plus named presets
in `~/.config/gst-rknn/nanotracker-benchmark-last-run.yaml`. Select one from the
scrollable recent/preset list to reload it; enter a preset name and choose
**Save** to retain the current form, or **Rename** to rename the selected preset.
Use the **Browse** button beside Ground truth to choose its CSV on the Radxa.

Use **Play source** to stream the selected file or image sequence without a
tracker or ROI. It records a source-only run; client display FPS is available,
but tracker-specific CSV, confidence, and IoU results are intentionally absent.

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

On the development host, update `client.yaml` when its receiving LAN IP changes,
then run `python3 apps/nanotracker_benchmark/client.py`.

The desktop client uses the same system packages as the existing Python viewer:
PyGObject/GStreamer, OpenCV, NumPy, and PyYAML. The Radxa setup installs an
application-local `uv` binary and creates `.venv` with system PyGObject access
so it can decode previews without modifying Ubuntu's managed Python.

Each Radxa run is saved under `/home/radxa/gst-rknn/benchmarks/<run-id>/` with
the request, exact pipeline, log, prediction CSV, JSON summary, and IoU report
when the dataset has ground truth. Server and client FPS are intentionally
separate from tracker-only `fakesink` benchmarks.
