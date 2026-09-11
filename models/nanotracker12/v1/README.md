# NanoTracker V1

Original ONNX models are from [HonglinChu/SiamTrackers](https://github.com/HonglinChu/SiamTrackers), commit `248663f`, `NanoTrack/models/nanotrackv1`.

The model has a 48-channel backbone and a 16×16 head output. V1 uses window
influence 0.462, penalty 0.148, and learning rate 0.390 from `configv1.yaml`.

`onnx/` keeps upstream source names. Run the scripts in `tools/` to create the
127×127 template export, synthetic calibration features, and `rknn/` files.
