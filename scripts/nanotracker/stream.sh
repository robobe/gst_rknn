#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
# Defaults match tools/video-metadata-viewer; override for another LAN host.
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
stream_host=${VIDEO_METADATA_HOST:-10.100.102.15}
video_port=${VIDEO_METADATA_VIDEO_PORT:-5004}
metadata_port=${VIDEO_METADATA_METADATA_PORT:-5005}
environment="GST_PLUGIN_PATH='$remote_root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"

pipeline="$environment gst-launch-1.0 -q filesrc location='$remote_root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360,framerate=30/1 ! rknnnanotrack enabled=true roi='20,148,64,64' models-dir='$remote_root/models/nanotracker' precision=mixed resize=cpu ! roi2udp host='$stream_host' port=$metadata_port ! videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=30 bframes=0 ! h264parse ! rtph264pay pt=96 config-interval=1 ! udpsink host='$stream_host' port=$video_port sync=false async=false"

printf 'Streaming from %s:\n%s\n' "$target" "$pipeline"
ssh "$target" "$pipeline"
