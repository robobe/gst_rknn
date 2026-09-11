# NanoTracker V2

Original ONNX models are from [HonglinChu/SiamTrackers](https://github.com/HonglinChu/SiamTrackers), commit `248663f`, `NanoTrack/models/nanotrackv2`.

The model has a 48-channel backbone and a 16×16 head output. V2 uses window
influence 0.490, penalty 0.150, and learning rate 0.385 from `configv2.yaml`.

`onnx/` keeps upstream source names. Run the scripts in `tools/` to create the
127×127 template export, synthetic calibration features, and `rknn/` files.
