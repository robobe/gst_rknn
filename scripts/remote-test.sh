#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
environment="GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"

usage() {
  printf '%s\n' \
    "usage: $0 {inspect|smoke}" \
    "  inspect  show the deployed rknnhello element" \
    "  smoke    run rknnhello through a one-frame pipeline"
}

case "${1:-}" in
  inspect) ssh "$target" "$environment gst-inspect-1.0 rknnhello" ;;
  smoke)
    output=$(ssh "$target" "$environment gst-launch-1.0 -q videotestsrc num-buffers=1 ! video/x-raw,format=RGB ! rknnhello ! fakesink" 2>&1)
    printf '%s\n' "$output"
    case "$output" in *"Hello Radxa"*) ;; *) echo "rknnhello did not print its greeting" >&2; exit 1 ;; esac
    ;;
  *) usage >&2; exit 2 ;;
esac
