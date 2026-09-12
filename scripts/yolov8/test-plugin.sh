#!/usr/bin/env bash
set -euo pipefail

root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
remote_model=${YOLO_MODEL:-"$remote_root/models/yolov8/rknn/yolov8n-rk3566-int8.rknn"}
resize=${YOLO_RESIZE:-auto}
confidence=${YOLO_CONFIDENCE:-0.25}
output=$(mktemp)
trap 'rm -f "$output"' EXIT

cmake --preset radxa-debug
cmake --build --preset radxa-debug --target gstrknnyolov8 gstroi2csv
"$root/scripts/deploy.sh" models
"$root/scripts/deploy.sh" plugin
ssh "$target" "GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin gst-inspect-1.0 rknnyolov8"
ssh "$target" "rm -f /tmp/yolov8-smoke.csv; GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin gst-launch-1.0 -q filesrc location='$remote_root/models/yolov8/testdata/bus.jpg' ! jpegdec ! videoconvert ! video/x-raw,format=RGB ! rknnyolov8 model='$remote_model' resize='$resize' confidence-threshold='$confidence' ! roi2csv location=/tmp/yolov8-smoke.csv ! fakesink"
rsync -a "$target:/tmp/yolov8-smoke.csv" "$output"
python3 "$root/tools/validate_yolov8_roi_csv.py" "$output"
