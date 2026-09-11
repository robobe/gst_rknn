#!/usr/bin/env bash
set -euo pipefail

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${BUILD_DIR:-"$project_root/build/radxa-debug"}
target="${RADXA_USER:-radxa}@${RADXA_HOST:-radxa}"
remote_root=${RADXA_ROOT:-/home/radxa/gst-rknn}

usage() { echo "usage: $0 {plugin|models|assets|datasets|benchmark|benchmark-setup|all}" >&2; exit 2; }

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
  # NanoTrackV3 predates the per-version model tree and resolves models at its root.
  if compgen -G "$project_root/models/nanotracker/rknn/*.rknn" >/dev/null; then
    rsync -a "$project_root/models/nanotracker/rknn/"*.rknn "$target:$remote_root/models/nanotracker/"
  fi
}

deploy_assets() {
  ssh "$target" "mkdir -p '$remote_root/assets'"
  rsync -a "$project_root/assets/" "$target:$remote_root/assets/"
  rsync -a "$project_root/src/diagnostics/compare_nanotracker_csv.py" "$target:$remote_root/assets/nanotracker/"
}

deploy_datasets() {
  datasets_dir=${DATASETS_DIR:-/home/user/datasets}
  test -d "$datasets_dir" || { echo "No dataset directory at $datasets_dir" >&2; exit 1; }
  ssh "$target" "mkdir -p '$remote_root/datasets'"
  rsync -a --info=progress2 "$datasets_dir/" "$target:$remote_root/datasets/"
}

deploy_benchmark() {
  ssh "$target" "mkdir -p '$remote_root/apps'"
  rsync -a --delete --exclude '__pycache__' --exclude '.venv' --exclude '.uv-bin' "$project_root/apps/nanotracker_benchmark/" "$target:$remote_root/apps/nanotracker_benchmark/"
}

setup_benchmark() {
  deploy_benchmark
  ssh "$target" "chmod +x '$remote_root/apps/nanotracker_benchmark/install_server.sh'; '$remote_root/apps/nanotracker_benchmark/install_server.sh'"
}

case "${1:-}" in
  plugin) deploy_plugins ;;
  models) deploy_models ;;
  assets) deploy_assets ;;
  datasets) deploy_datasets ;;
  benchmark) deploy_benchmark ;;
  benchmark-setup) setup_benchmark ;;
  all) deploy_plugins; deploy_models; deploy_assets ;;
  *) usage ;;
esac
