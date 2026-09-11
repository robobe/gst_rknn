# NanoTracker V1/V2 models

This tree keeps V1 and V2 independent. Each version contains the original ONNX
exports, generated RKNN files, conversion tools, and a version-specific README.

The plugin resolves `models-dir/v1/rknn` or `models-dir/v2/rknn`; therefore
deploy this whole `nanotracker12` directory, not individual files.

The default `mixed` set uses FP16 template and search backbones with an INT8
head. Rebuild a version on an Ubuntu x86_64 host with RKNN Toolkit2 2.3.0:

```sh
python3 v1/tools/make_template_onnx.py
python3 v1/tools/generate_calibration.py
python3 v1/tools/convert_rknn.py
```

Repeat for `v2`. `python3 v2/tools/convert_rknn.py --profile int8` builds the
optional fully quantized V2 profile. `generate_calibration.py` uses the repository's synthetic
moving-box video and GT CSV by default. It emits feature pairs required for
multi-input head calibration; the generated `tools/calibration/` directories
are intentionally ignored by Git.
