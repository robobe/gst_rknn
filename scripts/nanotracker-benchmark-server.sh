#!/usr/bin/env bash
set -euo pipefail
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}
exec ssh "$target" "cd '$remote_root/apps/nanotracker_benchmark' && exec .venv/bin/python server.py --config server.yaml"
