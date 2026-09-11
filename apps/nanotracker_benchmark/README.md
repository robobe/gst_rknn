# NanoTracker benchmark application

The Radxa server runs one selected NanoTrack V1/V2/V3 pipeline at a time and
streams H.264/RTP video on UDP 5004 plus ROI metadata on UDP 5005. The desktop
client browses `/home/radxa`, previews a source frame, selects the initial ROI,
and displays the result. Its server LED is green when the FastAPI health check
is reachable and red when the server cannot be contacted.

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

The server browser exposes it under `/home/radxa/gst-rknn/datasets`.

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
