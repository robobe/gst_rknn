# NanoTrackV3 ONNX to RKNN

This project targets an RK3566-class NPU. Confirm the board before converting:

```bash
tr -d '\0' </proc/device-tree/compatible; echo
```

Use [RKNN-Toolkit2](https://github.com/airockchip/rknn-toolkit2) on the development machine and set `target_platform='rk3566'`. Rockchip lists RK3566/RK3568 as Toolkit2 targets and separates conversion on the development machine from C/C++ runtime inference on the board. Keep the Toolkit2 release and the board's `librknnrt.so` from the same RKNPU2 SDK release. Do not use the older, incompatible `rknn-toolkit`.

This board currently reports `rknn_server` 2.3.0. Start with the matching
Toolkit2 2.3.0 package; upgrade Toolkit2 and the board runtime together, not
independently.

On the tested Python 3.12 conversion host, Toolkit2 2.3.0 needs
`onnx==1.16.2` (it uses the legacy `onnx.mapping` API) and `setuptools<81`
(it imports `pkg_resources`).

## Source ONNX files

Upstream [`NanoTrack/models/nanotrackv3`](https://github.com/HonglinChu/SiamTrackers/tree/master/NanoTrack/models/nanotrackv3) contains exactly:

| Upstream file | Fixed input | Output | Role |
| --- | --- | --- | --- |
| [`nanotrack_backbone.onnx`](https://github.com/HonglinChu/SiamTrackers/blob/master/NanoTrack/models/nanotrackv3/nanotrack_backbone.onnx) | `1x3x255x255` | `1x96x16x16` | Per-frame search backbone |
| [`nanotrack_head.onnx`](https://github.com/HonglinChu/SiamTrackers/blob/master/NanoTrack/models/nanotrackv3/nanotrack_head.onnx) | `1x96x8x8`, `1x96x16x16` | `1x2x15x15`, `1x4x15x15` | Classification and box regression |

The plugin also requires `nanotrack_backbone_template.onnx`: the same backbone graph re-shaped to input `1x3x127x127` and output `1x96x8x8`. It is not in upstream; it must be derived without changing weights. The three ONNX files must retain these shapes because the plugin validates them at load time.

## Conversion sequence

1. Download the two upstream ONNX files into `models/nanotracker/onnx/`; create the 127-pixel template ONNX from the backbone.
2. Convert each fixed-shape ONNX separately with RKNN Toolkit2: `RKNN()`, `config(target_platform='rk3566', ...)`, `load_onnx(...)`, `build(...)`, and `export_rknn(...)`. Rockchip's [ONNX example](https://github.com/airockchip/rknn-toolkit2/blob/master/rknn-toolkit2/examples/onnx/yolov5/test.py) and [accuracy-analysis example](https://github.com/airockchip/rknn-toolkit2/blob/master/rknn-toolkit2/examples/functions/accuracy_analysis/test.py) use this flow.
3. First produce an FP16 baseline (`do_quantization=False`) for all three graphs. Then make INT8 candidates (`do_quantization=True`) and compare their tracking output with the baseline on the same clips.
4. Deploy a matching filename set. The plugin resolves names as follows:

| `precision` property | Backbones | Head |
| --- | --- | --- |
| `fp16` | no suffix | no suffix |
| `mixed` | no suffix | `_int8` |
| `int8` | `_int8` | `_int8` |
| `int8-mmse` | `_int8_mmse` | `_int8_mmse` |

For example, `mixed` loads `nanotrack_backbone_template.rknn`, `nanotrack_backbone.rknn`, and `nanotrack_head_int8.rknn`, which is the starter set already deployed here.

## Calibration and quantization

Start with `mixed`: keep template/search backbones FP16 and quantize only the head to INT8. It limits accuracy risk while the per-frame head still runs on the NPU. Make the calibration data representative of deployment: varied target sizes, backgrounds, light, motion blur, and crops from actual tracking sequences—not arbitrary classification images. Use separate datasets whose sample shapes match each graph: 127x127 BGR template crops, 255x255 BGR search crops, and correctly paired `96x8x8` / `96x16x16` head features. Preserve the plugin's BGR input and its existing crop/resize behavior during calibration.

Rockchip's examples show `build(do_quantization=True, dataset=...)`, `accuracy_analysis(...)`, and a per-channel MMSE configuration (`quantized_method='channel', quantized_algorithm='mmse'`). Try default INT8 first, then `int8-mmse`; retain it only if sequence-level tracking quality improves. Rockchip's [MMSE example](https://github.com/airockchip/rknn-toolkit2/blob/master/rknn-toolkit2/examples/functions/quantize_algorithm_mmse/test.py) is the reference. If one or two sensitive layers cause the regression, use Toolkit2's [hybrid quantization](https://github.com/airockchip/rknn-toolkit2/tree/master/rknn-toolkit2/examples/functions/hybrid_quant): step 1 produces a configuration, then mark only measured-problem layers `float16` and run step 2. Do not guess the layers.

## Performance on Radxa Zero 3W

Measure the entire GStreamer pipeline, not only `rknn_run`: it includes two resizes/crops, memory synchronization, three networks, decoding, and post-processing. Compare `precision=fp16`, `mixed`, `int8`, and `int8-mmse` with the same video, ROI, clocks, `resize=cpu`, and `resize=auto`; record both FPS and tracker CSV IoU. The existing NanoTracker scripts produce the CSV comparison. Keep the fastest variant that meets the agreed IoU/track-loss threshold.

The backbone runs once for initialization and once per video frame; the head runs per frame. That makes the search backbone and head the first candidates to benchmark. Avoid changing 127, 255, or the feature/output shapes to chase speed: they are model geometry, not runtime tuning knobs. If quantization fails quality validation, FP16/mixed is the practical answer; accuracy is more valuable than a nominally faster tracker that loses the object.

## Primary sources

- [Rockchip RKNN-Toolkit2 README](https://github.com/airockchip/rknn-toolkit2/blob/master/README.md): supported platforms, conversion/runtime roles, and current releases.
- [Rockchip accuracy analysis example](https://github.com/airockchip/rknn-toolkit2/blob/master/rknn-toolkit2/examples/functions/accuracy_analysis/test.py): `config`, ONNX loading, quantized build, and `accuracy_analysis` API usage.
- [Rockchip MMSE example](https://github.com/airockchip/rknn-toolkit2/blob/master/rknn-toolkit2/examples/functions/quantize_algorithm_mmse/test.py): per-channel/MMSE settings.
- [Rockchip hybrid quant example](https://github.com/airockchip/rknn-toolkit2/tree/master/rknn-toolkit2/examples/functions/hybrid_quant): two-step selective FP16/INT8 workflow.
- [NanoTrackV3 upstream models](https://github.com/HonglinChu/SiamTrackers/tree/master/NanoTrack/models/nanotrackv3): source ONNX artifacts.
