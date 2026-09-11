# NanoTracker V2 30-FPS optimization

## Goal

Reach a median sustained 30 FPS or better for V2 on the Radxa RK3566 using the
500-frame, 640×360 synthetic video, with `fakesink sync=false` and tracker ROI
metadata attached. Every decoded frame remains an NPU tracking update.

## Design

The plugin remains `rknnnanotracker12`; there is no replacement model or new
element. The public BGR caps, properties, `nanotrack` ROI metadata, RGA/CPU
resize behavior, and V1 support remain compatible.

The optimized V2 inference path owns RKNN tensor memory for its lifetime:

1. RGA resizes each crop directly to RKNN image memory through its DMA FD.
2. The template and search backbone outputs remain in RKNN DMA memory.
3. The head imports those buffers through `rknn_create_mem_from_fd`.
4. Only the small head classification and localization outputs are synchronized
   to CPU for box decoding.

This removes per-frame backbone output download, float-vector allocation,
NCHW-to-NHWC transpose, and head-input upload. OpenCV remains the fallback if
RGA cannot resize a crop.

## Measurement and acceptance

`scripts/nanotracker12/test.sh bench v2` runs the non-CSV pipeline five times,
ignores the first warm-up run, and reports the median of the remaining four.
The acceptance threshold is at least 30 FPS.

The existing 500-frame CSV test is the correctness gate. It must create 500
matching rows with mean IoU at least 0.8833 and minimum IoU at least 0.8427
against `move_right_500.csv`. These values permit at most the agreed 0.03 drop
from the pre-optimization V2 mixed baseline.

## Model scope

The validated V2 full-INT8 profile is selected by the V2 scripts. Five passes
measured 50.79, 54.38, 51.38, 52.72, and 51.42 FPS; excluding warm-up, the
median is 52.07 FPS. It produced mean IoU 0.8968 and minimum IoU 0.8471. The
plugin's public default remains `mixed` for V1 compatibility; set
`precision=int8` for V2.
The conversion tool also supports `--profile int8-mmse` for future comparison.
