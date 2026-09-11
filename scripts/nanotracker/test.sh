#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
environment="GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"
precision="${NANOTRACK_PRECISION:-int8}"

usage() {
  printf '%s\n' \
    "usage: $0 {inspect|smoke|video|compare|bench}" \
    "  inspect  show the deployed NanoTracker element" \
    "  smoke    run 60 synthetic BGR frames" \
    "  video    run the 500-frame MP4 and write predictions.csv plus FPS" \
    "  compare  print IoU, FPS, and the recorded pipeline command" \
    "  bench    run five RGA/fakesink passes and print the post-warm-up median FPS"
}

case "${1:-}" in
  inspect)
    ssh "$target" "$environment gst-inspect-1.0 rknnnanotrack"
    ;;
  smoke)
    ssh "$target" "$environment gst-launch-1.0 -q videotestsrc num-buffers=60 ! videoconvert ! video/x-raw,format=BGR,width=320,height=240 ! rknnnanotrack enabled=true roi='80,60,64,64' models-dir='$remote_root/models/nanotracker' precision='$precision' resize=auto ! fakesink"
    ;;
  video)
    pipeline="$environment gst-launch-1.0 -q filesrc location='$remote_root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotrack enabled=true roi='20,148,64,64' models-dir='$remote_root/models/nanotracker' precision='$precision' resize=auto ! roi2csv location='$remote_root/assets/nanotracker/predictions.csv' ! fakesink sync=false"
    printf 'Running on %s:\n%s\n' "$target" "$pipeline"
    ssh "$target" "printf '%s\\n' \"$pipeline\" > '$remote_root/assets/nanotracker/run_pipeline.txt'; rm -f '$remote_root/assets/nanotracker/predictions.csv'; start=\$(date +%s%N); $pipeline; end=\$(date +%s%N); awk -v ns=\$((end-start)) 'BEGIN { printf \"elapsed_s=%.6f\\nfps=%.2f\\n\", ns/1e9, 500e9/ns }' > '$remote_root/assets/nanotracker/run_metrics.txt'; cat '$remote_root/assets/nanotracker/run_metrics.txt'"
    ;;
  compare)
    ssh "$target" "python3 '$remote_root/assets/nanotracker/compare_nanotracker_csv.py' '$remote_root/assets/nanotracker/move_right_500.csv' '$remote_root/assets/nanotracker/predictions.csv' --metrics '$remote_root/assets/nanotracker/run_metrics.txt' --pipeline '$remote_root/assets/nanotracker/run_pipeline.txt'"
    ;;
  bench)
    pipeline="$environment gst-launch-1.0 -q filesrc location='$remote_root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotrack enabled=true roi='20,148,64,64' models-dir='$remote_root/models/nanotracker' precision='$precision' resize=auto ! fakesink sync=false"
    printf 'Benchmarking on %s:\n%s\n' "$target" "$pipeline"
    ssh "$target" "for run in 1 2 3 4 5; do start=\$(date +%s%N); $pipeline; end=\$(date +%s%N); awk -v ns=\$((end-start)) -v r=\$run 'BEGIN { printf \"run=%d fps=%.2f\\n\", r, 500e9/ns }'; done" | tee /tmp/nanotracker-v3-bench.txt
    awk -F= '/fps=/{print $3}' /tmp/nanotracker-v3-bench.txt | tail -n +2 | sort -n | awk '{ values[NR]=$1 } END { if (NR != 4) exit 1; printf "median_fps=%.2f\\n", (values[2]+values[3])/2 }'
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
