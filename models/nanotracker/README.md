# NanoTrackV3 models

This directory contains mixed and full-INT8 RKNN artifacts for the
`rknnnanotrack` plugin. They target the Radxa Zero 3W RK3566 NPU.

`onnx/` contains the two upstream sources from NanoTrackV3. Before conversion,
create the required 127x127 template graph, then convert the models on an
x86_64 development machine with RKNN Toolkit 2:

```bash
python3 models/nanotracker/tools/make_template_onnx.py
python3 models/nanotracker/tools/generate_calibration.py
python3 models/nanotracker/tools/convert_rknn.py --profile mixed
```

New artifacts are written to `rknn/`; the existing root-level artifacts remain
the current working set until a converted set passes validation.

The generator creates representative image and paired head-feature tensors; do
not use arbitrary images for head INT8 calibration. See
[RKNN_CONVERSION.md](RKNN_CONVERSION.md) for source links, quantization, and
performance validation.

The current board runtime is RKNN 2.3.0, so use the matching Toolkit2 2.3.0
package for conversion.

The tested conversion-host dependency pins are `rknn-toolkit2==2.3.0`,
`onnx==1.16.2`, and `setuptools<81`.
`tools/generate_calibration.py` creates synthetic-video image and feature
calibration data. Build profiles with `tools/convert_rknn.py --profile mixed`,
`--profile int8`, or `--profile int8-mmse`. The selected V3 runtime profile is
`int8`: it reached 53.14 FPS, mean IoU 0.9367, and minimum IoU 0.8990. The
plugin property still defaults to `mixed` for compatibility; scripts select
INT8 and `NANOTRACK_PRECISION=mixed` restores the prior profile.
