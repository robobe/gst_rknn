#!/usr/bin/env bash
set -euo pipefail

sysroot=${RADXA_SYSROOT:-/home/user/sysroots/radxa}
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
"$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/ensure-rknn-toolkit.sh"
mkdir -p "$sysroot"

for directory in lib usr/lib usr/include usr/share/pkgconfig; do
  if ssh "$target" "test -d /$directory"; then
    mkdir -p "$sysroot/$directory"
    rsync -a "$target:/$directory/" "$sysroot/$directory/"
  fi
done
