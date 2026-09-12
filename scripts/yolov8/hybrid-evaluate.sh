#!/usr/bin/env bash
set -euo pipefail

root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
for profile in int8 hybrid-int8; do
  test -f "$root/models/yolov8/rknn/yolov8n-rk3566-$profile.rknn" || { echo "missing $profile model" >&2; exit 1; }
done
"$root/scripts/deploy.sh" models
"$root/scripts/deploy.sh" assets
for profile in int8 hybrid-int8; do
  ssh "$target" "python3 '$remote_root/models/yolov8/tools/smoke_test.py' --model '$remote_root/models/yolov8/rknn/yolov8n-rk3566-$profile.rknn'"
  ssh "$target" "python3 '$remote_root/models/yolov8/tools/benchmark_coco.py' --profile '$profile' --dataset '$remote_root/assets/coco_val_sample'"
done
for profile in int8 hybrid-int8; do
  rsync -a "$target:$remote_root/assets/coco_val_sample/predictions-$profile.json" "$target:$remote_root/assets/coco_val_sample/benchmark-$profile.json" "$root/assets/coco_val_sample/"
done
"$root/.venv-rknn/bin/python" "$root/tools/report_yolov8_hybrid_comparison.py"
