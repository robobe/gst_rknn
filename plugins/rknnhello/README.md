# rknnhello

Minimal video passthrough element used to verify the Radxa cross-build and
deployment path. It deliberately does not call RKNN Runtime yet.

Factory: `rknnhello`

```sh
videotestsrc num-buffers=1 ! video/x-raw,format=RGB ! rknnhello ! fakesink
```
