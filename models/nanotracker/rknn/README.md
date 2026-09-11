# Generated model set

`nanotrack_backbone_template.rknn` and `nanotrack_backbone.rknn` were generated
locally from the tracked ONNX files using RKNN Toolkit2 2.3.0 for `rk3566`.

`nanotrack_head_int8.rknn` is the existing validated reference head, copied
here because generating a new INT8 head requires representative paired feature
tensor calibration data. Replace it only after running the calibrated head
conversion and validating tracker CSV IoU.

Use this directory as the plugin `models-dir` with `precision=mixed`.
