# YOLOv8 RKNN GStreamer plugin

`rknnyolov8` runs a selected YOLOv8 RKNN model on progressive RGB video and
preserves pixels while attaching one `GstVideoRegionOfInterestMeta` per final
detection. The model is loaded once during the READY-to-PAUSED transition.

## Properties

| Property | Default | Description |
| --- | --- | --- |
| `model` | required | Exact path to an INT8 or hybrid-INT8 YOLOv8 RKNN file. |
| `confidence-threshold` | `0.25` | Minimum class confidence. |
| `nms-iou-threshold` | `0.45` | Same-class NMS IoU threshold. |
| `max-detections` | `100` | Maximum ROI metadata records per frame. |
| `resize` | `auto` | `auto` uses RGA and falls back permanently to CPU; `cpu` disables RGA. |

All properties are READY-only. Input and output caps are progressive
`video/x-raw,format=RGB`; use `videoconvert` before the element as needed.

## Metadata

Each detection has `roi_type="yolo8"`, a bounding box in original-frame
coordinates, and `id` set to the standard COCO category ID. Its `"yolo8"`
parameter structure contains `confidence` as a double. `roi2csv` and `roi2udp`
serialize the confidence and append `class_id`; existing tracker records keep
that new column empty.

## Radxa smoke test

```sh
bash scripts/yolov8/test-plugin.sh
```

The script cross-compiles, deploys the module and YOLO assets, runs
`gst-inspect-1.0`, then validates `bus.jpg` metadata against the five published
Model Zoo detections. Set `YOLO_MODEL` to test the deployed hybrid artifact or
`YOLO_RESIZE=cpu YOLO_CONFIDENCE=0.2` to exercise the CPU fallback with the
reference smoke threshold.
