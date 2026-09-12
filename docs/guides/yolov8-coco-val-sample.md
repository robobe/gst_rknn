# YOLOv8n RKNN COCO val sample

- Date: 2026-09-12T12:08:33Z
- Board: Radxa Zero 3W / RK3566
- Runtime: RKNN 2.3.2
- Model: `yolov8n-rk3566-int8.rknn` (Toolkit2 2.3.0 build)
- Dataset: 200 deterministic COCO val2017 images (seed 20260912)

| Metric | Result |
| --- | ---: |
| COCO mAP@[.50:.95] | 0.3195 |
| AP@.50 | 0.4336 |
| AP@.75 | 0.3474 |
| RKNN inference FPS (after 10 warm-up images) | 17.47 |
| End-to-end Python FPS | 7.25 |
| Detections | 941 |

Post-processing uses confidence 0.25 and per-class NMS IoU 0.45. Keep these settings and the sample seed unchanged when comparing runs.
