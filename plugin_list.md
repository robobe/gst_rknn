# Plugin list

| Plugin | Description |
| --- | --- |
| `rknnhello` | Minimal video passthrough filter that prints `Hello Radxa`; validates cross-build, deployment, and GStreamer loading. |
| `rknnnanotrack` | NanoTrackV3 single-object tracker that attaches ROI metadata to BGR video frames. |
| `rknnnanotracker12` | Independent NanoTrack V1/V2 single-object tracker; select its model with `model-version`. |
| `rknnyolov8` | YOLOv8 RKNN detector that attaches COCO-class ROI metadata to RGB video frames. |
| `roi2csv` | Diagnostics passthrough that records `GstVideoRegionOfInterestMeta` to CSV. |
| `roi2udp` | Diagnostics passthrough that sends one ROI metadata CSV record per UDP datagram. |
