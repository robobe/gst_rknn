#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
environment="GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"
precision="${NANOTRACK_PRECISION:-int8}"

usage() {
  printf '%s\n' \
    "usage: $0 {inspect|smoke|video|compare|bench|matrix}" \
    "  inspect  show the deployed NanoTracker element" \
    "  smoke    run 60 synthetic BGR frames" \
    "  video    run the 500-frame MP4 and write predictions.csv plus FPS" \
    "  compare  print IoU, FPS, and the recorded pipeline command" \
    "  bench    run five RGA/fakesink passes and print the post-warm-up median FPS" \
    "  matrix   compare deployed V3 profiles and generate the guide table/chart"
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
  matrix)
    results_dir="$project_root/docs/guides/images"
    results_csv="$results_dir/nanotracker-v3-profile-results.csv"
    mkdir -p "$results_dir"
    printf '%s\n' 'profile,median_fps,mean_iou,min_iou,matched_frames,timestamp_utc' > "$results_csv"
    for profile in mixed int8 int8-mmse; do
      echo "Measuring $profile on $target"
      output=$(ssh "$target" bash -s -- "$remote_root" "$profile" <<'EOF'
set -euo pipefail
root=$1
profile=$2
env=(env "GST_PLUGIN_PATH=$root/plugins" GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin)
asset="$root/assets/nanotracker"
prediction="$asset/predictions-$profile.csv"
pipeline=(filesrc "location=$asset/move_right_500.mp4" ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotrack enabled=true "roi=20,148,64,64" "models-dir=$root/models/nanotracker" "precision=$profile" resize=auto ! roi2csv "location=$prediction" ! fakesink sync=false)
rm -f "$prediction"
start=$(date +%s%N)
"${env[@]}" gst-launch-1.0 -q "${pipeline[@]}"
end=$(date +%s%N)
video_fps=$(awk -v ns=$((end-start)) 'BEGIN { printf "%.2f", 500e9/ns }')
comparison=$(python3 "$asset/compare_nanotracker_csv.py" "$asset/move_right_500.csv" "$prediction")
mean_iou=$(awk '/mean IoU:/ {print $3}' <<<"$comparison")
min_iou=$(awk '/minimum IoU:/ {print $3}' <<<"$comparison")
matched=$(awk '/matched rows:/ {print $3}' <<<"$comparison")
rates=()
bench=(filesrc "location=$asset/move_right_500.mp4" ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360 ! rknnnanotrack enabled=true "roi=20,148,64,64" "models-dir=$root/models/nanotracker" "precision=$profile" resize=auto ! fakesink sync=false)
for run in 1 2 3 4 5; do
  start=$(date +%s%N)
  "${env[@]}" gst-launch-1.0 -q "${bench[@]}"
  end=$(date +%s%N)
  rates+=("$(awk -v ns=$((end-start)) 'BEGIN { printf "%.2f", 500e9/ns }')")
done
median=$(printf '%s\n' "${rates[@]:1}" | sort -n | awk '{ values[NR]=$1 } END { printf "%.2f", (values[2]+values[3])/2 }')
printf 'video_fps=%s\nmean_iou=%s\nmin_iou=%s\nmatched=%s\nmedian_fps=%s\n' "$video_fps" "$mean_iou" "$min_iou" "$matched" "$median"
EOF
)
      median=$(awk -F= '/^median_fps=/{print $2}' <<<"$output")
      mean=$(awk -F= '/^mean_iou=/{print $2}' <<<"$output")
      minimum=$(awk -F= '/^min_iou=/{print $2}' <<<"$output")
      matched=$(awk -F= '/^matched=/{print $2}' <<<"$output")
      test -n "$median" -a -n "$mean" -a -n "$minimum" -a -n "$matched"
      printf '%s,%s,%s,%s,%s,%s\n' "$profile" "$median" "$mean" "$minimum" "$matched" "$(date -u +%FT%TZ)" >> "$results_csv"
      printf '%-10s median_fps=%s mean_iou=%s min_iou=%s matched=%s\n' "$profile" "$median" "$mean" "$minimum" "$matched"
    done
    python3 "$project_root/tools/render_nanotracker_v3_comparison.py" "$results_csv" \
      --svg "$results_dir/nanotracker-v3-profile-comparison.svg" \
      --guide "$project_root/docs/guides/nanotracker-v3-run-and-measure.md"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
