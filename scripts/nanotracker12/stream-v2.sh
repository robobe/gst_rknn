#!/usr/bin/env bash
set -euo pipefail

target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
root="${RADXA_ROOT:-/home/radxa/gst-rknn}"
host="${VIDEO_METADATA_HOST:-10.100.102.15}"
video_port="${VIDEO_METADATA_VIDEO_PORT:-5004}"
metadata_port="${VIDEO_METADATA_METADATA_PORT:-5005}"
env="GST_PLUGIN_PATH='$root/plugins' GST_REGISTRY_1_0=/tmp/gst-rknn-registry.bin"

pipe="$env gst-launch-1.0 -q filesrc location='$root/assets/nanotracker/move_right_500.mp4' ! decodebin ! videoconvert ! video/x-raw,format=BGR,width=640,height=360,framerate=30/1 ! rknnnanotracker12 enabled=true roi='20,148,64,64' models-dir='$root/models/nanotracker12' model-version=v2 precision=int8 resize=auto ! roi2udp host='$host' port=$metadata_port ! videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=30 bframes=0 ! h264parse ! rtph264pay pt=96 config-interval=1 ! udpsink host='$host' port=$video_port sync=true async=false"
printf 'Streaming NanoTracker V2 from %s:\n%s\n' "$target" "$pipe"
ssh "$target" "$pipe"
