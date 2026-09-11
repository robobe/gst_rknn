# NanoTracker V3 30-FPS optimization

V3 already used persistent RKNN tensor memory, RGA-to-DMA image input, and
DMA-backed backbone-to-head feature sharing. No V3 plugin rewrite was needed.

The optimization adds reproducible synthetic-video calibration and three RKNN
profiles: mixed, INT8, and INT8-MMSE. V3 resolves model names directly from
`models/nanotracker`, so deployment also publishes the generated `rknn/*.rknn`
files to that runtime directory.

The selected `precision=int8` profile passed the 500-frame validation with 500
matching ROI records, mean IoU 0.9367, and minimum IoU 0.8990. Its five-pass
640×360 RGA/fakesink rates were 52.84, 52.72, 52.81, 52.70, and 53.32 FPS;
the post-warm-up median was 52.77 FPS. INT8-MMSE achieved mean IoU 0.9428,
minimum IoU 0.8988, and 52.79 FPS, so it is retained as an accuracy-oriented
alternative rather than the selected speed profile.

Run `scripts/nanotracker/test.sh bench` for five passes; it discards warm-up
and reports the post-warm-up median. Set `NANOTRACK_PRECISION=mixed` or
`int8-mmse` to compare profiles.
