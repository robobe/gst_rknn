# NanoTracker tools

Run these commands from the repository root. Build and deploy the tracker first:

```bash
cmake --build --preset radxa-debug
./scripts/deploy.sh all
```

## 1. Check metadata packets

On the host, start the UDP monitor:

```bash
python3 tools/roi_udp_monitor.py
```

It listens on UDP 5005 and prints packet count and packet FPS every second.

## 2. Check video only

On the host:

```bash
bash tools/run_recv_pipe.sh
```

It displays H.264/RTP video from UDP 5004 and overlays FPS.

## 3. Check video and tracker box

On the host:

```bash
python3 tools/udp_bbox_viewer.py
```

It displays video from UDP 5004, receives ROI CSV datagrams on UDP 5005, and
draws the latest tracker box with Cairo.

## Send the test stream

Start one host tool before running this from the development machine:

```bash
./scripts/nanotracker/stream.sh
```

The default destination is `10.100.102.15`. Override it when the host address
changes:

```bash
VIDEO_METADATA_HOST=192.168.1.10 ./scripts/nanotracker/stream.sh
```
