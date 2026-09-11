#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
root="${RADXA_ROOT:-/home/radxa/gst-rknn}"
env="GST_PLUGIN_PATH='$root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"
version="${2:-v2}"
precision="${NANOTRACK_PRECISION:-mixed}"
[[ "$version" == v2 && -z "${NANOTRACK_PRECISION:-}" ]] && precision=int8

case "${1:-}" in
  inspect) ssh "$target" "$env gst-inspect-1.0 rknnnanotracker12" ;;
  smoke)
    [[ "$version" == v1 || "$version" == v2 ]] || { echo 'version must be v1 or v2' >&2; exit 2; }
    pipe="$env gst-launch-1.0 -q videotestsrc num-buffers=60 ! videoconvert ! video/x-raw,format=BGR,width=320,height=240 ! rknnnanotracker12 enabled=true roi='80,60,64,64' models-dir='$root/models/nanotracker12' model-version='$version' precision='$precision' resize=auto ! fakesink"
    printf 'Running on %s:\n%s\n' "$target" "$pipe"
    ssh "$target" "$pipe"
    ;;
  video)
    [[ "$version" == v1 || "$version" == v2 ]] || { echo 'version must be v1 or v2' >&2; exit 2; }
    output="$root/assets/nanotracker/predictions_${version}12.csv"
    pipe="$env gst-launch-1.0 -q filesrc location='$root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotracker12 enabled=true roi='20,148,64,64' models-dir='$root/models/nanotracker12' model-version='$version' precision='$precision' resize=auto ! roi2csv location='$output' ! fakesink sync=false"
    printf 'Running on %s:\n%s\n' "$target" "$pipe"
    ssh "$target" "rm -f '$output'; $pipe; wc -l '$output'"
    ;;
  bench)
    [[ "$version" == v2 ]] || { echo 'bench currently supports v2 only' >&2; exit 2; }
    pipe="$env gst-launch-1.0 -q filesrc location='$root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotracker12 enabled=true roi='20,148,64,64' models-dir='$root/models/nanotracker12' model-version=v2 precision='$precision' resize=auto ! fakesink sync=false"
    printf 'Benchmarking on %s:\n%s\n' "$target" "$pipe"
    ssh "$target" "for run in 1 2 3 4 5; do start=\$(date +%s%N); $pipe; end=\$(date +%s%N); awk -v n=\$((end-start)) -v r=\$run 'BEGIN { printf \"run=%d fps=%.2f\\n\", r, 500e9/n }'; done" | tee /tmp/nanotracker12-v2-bench.txt
    awk -F= '/fps=/{print $3}' /tmp/nanotracker12-v2-bench.txt | tail -n +2 | sort -n | awk '{ values[NR]=$1 } END { if (NR != 4) exit 1; printf "median_fps=%.2f\\n", (values[2]+values[3])/2 }'
    ;;
  *) echo "usage: $0 {inspect|smoke|video|bench [v1|v2]}" >&2; exit 2 ;;
esac
