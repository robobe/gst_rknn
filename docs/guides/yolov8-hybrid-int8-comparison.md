# YOLOv8n RK3566 INT8 vs hybrid-INT8

- Date: 2026-09-12T14:57:05Z
- Board: Radxa Zero 3W / RK3566; Runtime: RKNN 2.3.2
- Source: Rockchip Model Zoo YOLOv8n ONNX commit `bad6c7334531becaf90a561988519b7bec34d0ab`, SHA-256 `0c8716701f471067932b797eeb67c8e5db47c693c2557c881d7679ec12e21bc5`
- Calibration: identical deterministic 200-image COCO train2017 sample, seed 20260912
- Evaluation: 200 deterministic COCO val2017 images, seed 20260912; confidence 0.25, per-class NMS IoU 0.45

| Profile | Toolkit build | Model MiB | mAP@[.50:.95] | AP@.50 | AP@.75 | RKNN inference FPS | End-to-end Python FPS | Detections |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| int8 | 2.3.2 | 4.59 | 0.3308 | 0.4395 | 0.3603 | 17.61 | 7.35 | 943 |
| hybrid-int8 | 2.3.2 | 4.58 | 0.3300 | 0.4401 | 0.3566 | 16.21 | 7.07 | 947 |

Hybrid FP16 output tensors: `318`, `onnx::ReduceSum_326`, `331`, `338`, `onnx::ReduceSum_346`, `350`, `357`, `onnx::ReduceSum_365`, `369`.

Hybrid acceptance requires higher mAP@[.50:.95] and at least 85% of INT8 inference FPS (14.97 FPS). Pure INT8 is the default if it matches or beats hybrid mAP while remaining at least as fast. Recommend `int8`.
