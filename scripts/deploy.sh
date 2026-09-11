#!/usr/bin/env bash
set -euo pipefail

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${BUILD_DIR:-"$project_root/build/radxa-debug"}
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}

usage() { echo "usage: $0 {plugin|models|assets|all}" >&2; exit 2; }

deploy_plugins() {
  test -d "$build_dir/plugins" || { echo "No plugin output at $build_dir/plugins; build first." >&2; exit 1; }
  mapfile -d '' plugins < <(find "$build_dir/plugins" -type f -name '*.so' -print0)
  ((${#plugins[@]})) || { echo "No plugin modules at $build_dir/plugins; build first." >&2; exit 1; }
  ssh "$target" "mkdir -p '$remote_root/plugins'"
  rsync -a "${plugins[@]}" "$target:$remote_root/plugins/"
  rsync -a "$project_root/plugin_list.md" "$target:$remote_root/plugin_list.md"
}

deploy_models() {
  ssh "$target" "mkdir -p '$remote_root/models'"
  rsync -a "$project_root/models/" "$target:$remote_root/models/"
}

deploy_assets() {
  ssh "$target" "mkdir -p '$remote_root/assets'"
  rsync -a "$project_root/assets/" "$target:$remote_root/assets/"
  rsync -a "$project_root/src/diagnostics/compare_nanotracker_csv.py" "$target:$remote_root/assets/nanotracker/"
}

case "${1:-}" in
  plugin) deploy_plugins ;;
  models) deploy_models ;;
  assets) deploy_assets ;;
  all) deploy_plugins; deploy_models; deploy_assets ;;
  *) usage ;;
esac
