# NanoTrackV3

`rknnnanotrack` follows one user-selected object using the three NanoTrackV3 RKNN models. It preserves input pixels and attaches `nanotrack` `GstVideoRegionOfInterestMeta` to every active frame; it does not draw a box.

## Properties

| Property | Default | Description |
| --- | --- | --- |
| `enabled` | `false` | Enables tracking. A false-to-true transition initializes a fresh template from `roi` on the next frame. |
| `roi` | empty | Initial `x,y,width,height` rectangle in input-frame pixels. Setting it resets tracking on the next active frame. |
| `models-dir` | empty | Directory containing the selected three RKNN model files. Required while tracking is enabled. |
| `precision` | `mixed` | Filename set: `fp16`, `mixed`, `int8`, or `int8-mmse`. The deployed starter set supports `mixed`. |
| `resize` | `auto` | `auto` attempts RGA hardware resize and permanently falls back to OpenCV CPU resize for that instance after an RGA failure. `cpu` always uses OpenCV. |

Input must be progressive `video/x-raw,format=BGR`. Use `videoconvert` before the element for other formats.

## Smoke pipeline

```sh
GST_PLUGIN_PATH=/home/radxa/gst-rknn/plugins gst-launch-1.0 -q videotestsrc num-buffers=60 ! videoconvert ! video/x-raw,format=BGR,width=320,height=240 ! rknnnanotrack enabled=true roi="80,60,64,64" models-dir=/home/radxa/gst-rknn/models/nanotracker precision=mixed resize=auto ! fakesink
```

## Performance review

No real-video performance claim has been made. The active path runs the search backbone and head for every frame; it also allocates/copies a padded BGR crop before resizing. `auto` uses RGA when available, otherwise OpenCV CPU resize.

Measure end-to-end FPS and element latency on the same video for `resize=auto` and `resize=cpu` before changing code. Likely follow-up work: reuse crop buffers, evaluate decoder DMABuf/RGA/RKNN interop, and compare model precision against tracking accuracy.
