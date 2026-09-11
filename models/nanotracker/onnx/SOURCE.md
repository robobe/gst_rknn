# NanoTrackV3 ONNX source

Downloaded from [HonglinChu/SiamTrackers](https://github.com/HonglinChu/SiamTrackers/tree/248663fde6bf7c40190cf10ee396d5662919ecd3/NanoTrack/models/nanotrackv3), commit `248663fde6bf7c40190cf10ee396d5662919ecd3`.

| File | SHA-256 |
| --- | --- |
| `nanotrack_backbone.onnx` | `50be1320abf9384fd3479ea829f95e244cf3f3838190c5ab60c750fb8c1ce828` |
| `nanotrack_head.onnx` | `75357903be3f4817c965af16cb5a11fd32b1467f597a408405a98635ac63f61d` |

`nanotrack_backbone_template.onnx` is derived locally by
`../tools/make_template_onnx.py`; it is intentionally not downloaded because
upstream does not provide the required 127x127 variant.
