# NanoTrack version compatibility

The upstream [NanoTrack source](https://github.com/HonglinChu/SiamTrackers/tree/master/NanoTrack)
ships different ONNX interfaces for each version.

| Version | Backbone feature | Head outputs | Compatible with `rknnnanotrack` |
| --- | --- | --- | --- |
| V1 | 48x8x8 template, 48x16x16 search | 2x16x16 classification, 4x16x16 boxes | No |
| V2 | 48x8x8 template, 48x16x16 search | 2x16x16 classification, 4x16x16 boxes | No |
| V3 | 96x8x8 template, 96x16x16 search | 2x15x15 classification, 4x15x15 boxes | Yes |

All three use 127x127 template crops, 255x255 search crops, and stride 16, but
that does not make their models interchangeable. V1/V2 use the original
`mobilenetv3_small` backbone and V3 uses `mobilenetv3_small_v3`; V3 also has
different score-map geometry and tracker tuning constants.

This project's plugin checks V3 tensor shapes at startup and decodes a 15x15
map using V3 constants. Loading V1 or V2 would fail the shape check; bypassing
it would produce wrong tracking coordinates. Supporting either version needs a
separate model-profile branch for tensor validation, output decoding, and the
version-specific tracker parameters.

Primary upstream references:

- [V1 config](https://github.com/HonglinChu/SiamTrackers/blob/master/NanoTrack/models/config/configv1.yaml)
- [V2 config](https://github.com/HonglinChu/SiamTrackers/blob/master/NanoTrack/models/config/configv2.yaml)
- [V3 config](https://github.com/HonglinChu/SiamTrackers/blob/master/NanoTrack/models/config/configv3.yaml)
- [V1/V2/V3 ONNX model folders](https://github.com/HonglinChu/SiamTrackers/tree/master/NanoTrack/models)
