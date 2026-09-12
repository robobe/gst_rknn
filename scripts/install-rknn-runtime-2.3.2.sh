#!/usr/bin/env bash
set -euo pipefail

stage=${1:-/home/radxa/gst-rknn/rknn-runtime-2.3.2}
test "${EUID:-$(id -u)}" -eq 0 || { echo "run with sudo: sudo $0 [stage-dir]" >&2; exit 1; }
test -f "$stage/librknnrt.so" -a -f "$stage/rknn_server" || { echo "missing runtime files in $stage" >&2; exit 1; }
(cd "$stage" && printf '%s\n' \
  'd31fc19c85b85f6091b2bd0f6af9d962d5264a4e410bfb536402ec92bac738e8  librknnrt.so' \
  'eea12fe4270fad8aff015056319705b2eb871563ebd001eff8d8788bdd1c0cfa  rknn_server' | sha256sum -c -)

backup=/var/backups/rknn-2.3.0-$(date +%Y%m%d%H%M%S)
install -d -m 755 "$backup"
(cd / && cp -a --parents usr/bin/rknn_server usr/lib/aarch64-linux-gnu/librknnrt.so* usr/lib/aarch64-linux-gnu/librknn_api.so usr/lib/librknnrt.so usr/lib/librknn_api.so "$backup/")
install -m 755 "$stage/rknn_server" /usr/bin/rknn_server
install -m 644 "$stage/librknnrt.so" /usr/lib/aarch64-linux-gnu/librknnrt.so.2.3.2
ln -sfn librknnrt.so.2.3.2 /usr/lib/aarch64-linux-gnu/librknnrt.so
ln -sfn librknnrt.so.2.3.2 /usr/lib/aarch64-linux-gnu/librknnrt.so.1
ldconfig
ln -sfn librknnrt.so.2.3.2 /usr/lib/aarch64-linux-gnu/librknn_api.so
ln -sfn aarch64-linux-gnu/librknnrt.so.2.3.2 /usr/lib/librknnrt.so
ln -sfn aarch64-linux-gnu/librknnrt.so.2.3.2 /usr/lib/librknn_api.so
printf 'installed RKNN Runtime 2.3.2; backup: %s\nreboot before validation\n' "$backup"
