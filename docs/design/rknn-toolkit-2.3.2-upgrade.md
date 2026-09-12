# RKNN Toolkit2 2.3.2 upgrade record

## Purpose

Keep the RK3566 board runtime, the host converter, and the cross-build sysroot
on RKNN 2.3.2. The host guard is `scripts/ensure-rknn-toolkit.sh`; it creates
the untracked `.venv-rknn` with `uv` and pins Toolkit2 2.3.2, ONNX 1.16.2, and
`setuptools<81`. `scripts/sync-sysroot.sh` runs that guard first.

## 2.3.0 baseline

| Component | Observed version |
| --- | --- |
| Board | Radxa Zero 3W, Debian 12, aarch64, RK3566 |
| `rknn_server` | 2.3.0, build 2024-11-07 |
| `librknnrt.so` | 2.3.0 |
| Host converter | Toolkit2 2.3.0, Python 3.12.3 |

YOLOv8n INT8, built with Toolkit2 2.3.0, passed the Model Zoo `bus.jpg`
reference check:

| Detection | IoU | Score delta |
| --- | ---: | ---: |
| person | 0.991 | 0.038 |
| person | 0.990 | 0.031 |
| person | 0.983 | 0.017 |
| bus | 0.989 | 0.027 |
| person | 0.948 | 0.050 |

The current V3 INT8 baseline is 53.14 FPS, mean IoU 0.9367, and minimum IoU
0.8990. The current V2 INT8 baseline is 52.07 FPS, mean IoU 0.8968, and
minimum IoU 0.8471.

## Board upgrade

Download the official 2.3.2 files for Linux aarch64 from the `v2.3.2` tag:

- `rknpu2/runtime/Linux/librknn_api/aarch64/librknnrt.so`
- `rknpu2/runtime/Linux/rknn_server/aarch64/usr/bin/rknn_server`
- `rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`

Before replacement, back up `/usr/bin/rknn_server`,
`/usr/lib/aarch64-linux-gnu/librknnrt.so.2.3.0`, and deployed model folders.
Install the first two files as root, update the `librknnrt.so` symlinks, run
`ldconfig`, install the Lite2 wheel for the `radxa` user, then reboot. Verify
both server and runtime report 2.3.2 before running `./scripts/sync-sysroot.sh`.

`scripts/install-rknn-runtime-2.3.2.sh` performs the root-only runtime
replacement and creates a timestamped backup under `/var/backups`. It expects
the verified payload in `/home/radxa/gst-rknn/rknn-runtime-2.3.2`.

```sh
sudo /home/radxa/gst-rknn/scripts/install-rknn-runtime-2.3.2.sh
sudo reboot
```

## Validation record

1. Run existing 2.3.0 artifacts on Runtime 2.3.2: YOLOv8 smoke comparison,
   NanoTracker V3 matrix, and NanoTracker V1/V2 smoke, video, and benchmark.
2. Convert candidates with `.venv-rknn/bin/python`; do not overwrite accepted
   artifacts until candidates pass.
3. Repeat the same comparisons and record model hash, Toolkit2/runtime version,
   FPS, mean IoU, minimum IoU, and pass/fail here.

Accept YOLOv8 when all five Model Zoo reference detections retain IoU >= 0.80
and score delta <= 0.15. Accept V2 at >= 30 FPS, mean IoU >= 0.8833, and
minimum IoU >= 0.8427. Retain the fastest V3 profile preserving its current
tracking quality.

## 2.3.2 runtime validation

The board now reports `rknn_server` 2.3.2 (build 2025-03-30), `librknnrt.so`
2.3.2 (2025-04-09), and Lite2 2.3.2. The host `.venv-rknn` reports Python
3.12.3 and Toolkit2 2.3.2. Existing Toolkit2 2.3.0-built model artifacts were
used for these measurements; no models have been regenerated yet.

| Workload | Result | Status |
| --- | --- | --- |
| YOLOv8n `bus.jpg` reference | All five detections pass; IoU 0.948-0.991, score delta 0.017-0.050 | Pass |
| NanoTracker V3 mixed | 31.95 FPS, mean IoU 0.9344, minimum IoU 0.9125 | Quality pass; slower |
| NanoTracker V3 INT8 | 52.56 FPS, mean IoU 0.9367, minimum IoU 0.8990 | Pass |
| NanoTracker V3 INT8-MMSE | 53.05 FPS, mean IoU 0.9428, minimum IoU 0.8988 | Pass |
| NanoTracker V2 INT8 | 54.51 FPS post-warm-up median | Pass |

Keep V3 INT8 as the throughput default. INT8-MMSE is the accuracy-oriented
alternative. Do not select mixed on this runtime until its throughput drop is
explained.
