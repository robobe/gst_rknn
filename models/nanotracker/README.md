# NanoTrackV3 mixed model set

This directory contains the RKNN artifacts for the `rknnnanotrack` plugin:
FP16 template/search backbones and an INT8 head. They target the Radxa Zero 3W
RK3566 NPU.

`onnx/` contains the two upstream sources from NanoTrackV3. Before conversion,
create the required 127x127 template graph, then convert the models on an
x86_64 development machine with RKNN Toolkit 2:

```bash
python3 models/nanotracker/tools/make_template_onnx.py
python3 models/nanotracker/tools/convert_rknn.py --head-dataset head_features.txt
```

New artifacts are written to `rknn/`; the existing root-level artifacts remain
the current working set until a converted set passes validation.

`head_features.txt` must list representative, paired head feature tensors; do
not use arbitrary images for head INT8 calibration. See
[RKNN_CONVERSION.md](RKNN_CONVERSION.md) for source links, quantization, and
performance validation.

The current board runtime is RKNN 2.3.0, so use the matching Toolkit2 2.3.0
package for conversion.

The tested conversion-host dependency pins are `rknn-toolkit2==2.3.0`,
`onnx==1.16.2`, and `setuptools<81`.
