# Model assets

Create one directory per model, for example `models/yolov8/`. Put its `.rknn`
file and a README describing source, version, checksum, inputs, and outputs
there. `.rknn` files are intentionally not committed; `deploy.sh models` copies
this directory tree unchanged to the board.
