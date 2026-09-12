# YOLOv8n RKNN COCO val sample (int8)

- Date: 2026-09-12T14:57:53Z
- Board: Radxa Zero 3W / RK3566
- Runtime: RKNN 2.3.2
- Model: `yolov8n-rk3566-int8.rknn`
- Dataset: 200 deterministic COCO val2017 images (seed 20260912)

| Metric | Result |
| --- | ---: |
| COCO mAP@[.50:.95] | 0.3308 |
| AP@.50 | 0.4395 |
| AP@.75 | 0.3603 |
| RKNN inference FPS (after 10 warm-up images) | 17.61 |
| End-to-end Python FPS | 7.35 |
| Detections | 943 |

Post-processing uses confidence 0.25 and per-class NMS IoU 0.45. Keep these settings and the sample seed unchanged when comparing runs.
