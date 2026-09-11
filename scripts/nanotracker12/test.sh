#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
root="${RADXA_ROOT:-/home/radxa/gst-rknn}"
env="GST_PLUGIN_PATH='$root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"
version="${2:-v2}"

case "${1:-}" in
  inspect) ssh "$target" "$env gst-inspect-1.0 rknnnanotracker12" ;;
  smoke)
    [[ "$version" == v1 || "$version" == v2 ]] || { echo 'version must be v1 or v2' >&2; exit 2; }
    pipe="$env gst-launch-1.0 -q videotestsrc num-buffers=60 ! videoconvert ! video/x-raw,format=BGR,width=320,height=240 ! rknnnanotracker12 enabled=true roi='80,60,64,64' models-dir='$root/models/nanotracker12' model-version='$version' precision=mixed resize=auto ! fakesink"
    printf 'Running on %s:\n%s\n' "$target" "$pipe"
    ssh "$target" "$pipe"
    ;;
  video)
    [[ "$version" == v1 || "$version" == v2 ]] || { echo 'version must be v1 or v2' >&2; exit 2; }
    output="$root/assets/nanotracker/predictions_${version}12.csv"
    pipe="$env gst-launch-1.0 -q filesrc location='$root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotracker12 enabled=true roi='20,148,64,64' models-dir='$root/models/nanotracker12' model-version='$version' precision=mixed resize=auto ! roi2csv location='$output' ! fakesink sync=false"
    printf 'Running on %s:\n%s\n' "$target" "$pipe"
    ssh "$target" "rm -f '$output'; $pipe; wc -l '$output'"
    ;;
  *) echo "usage: $0 {inspect|smoke|video [v1|v2]}" >&2; exit 2 ;;
esac
