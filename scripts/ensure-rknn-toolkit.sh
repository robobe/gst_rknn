#!/usr/bin/env bash
set -euo pipefail

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
venv=${RKNN_VENV:-"$root/.venv-rknn"}
python=${PYTHON:-3.12}
version=2.3.2

command -v uv >/dev/null || { echo 'uv is required; install it first: https://docs.astral.sh/uv/' >&2; exit 1; }
if ! "$venv/bin/python" -c "import sys; from importlib.metadata import version as v; assert sys.version_info[:2] == (3, 12) and v('rknn-toolkit2') == '$version'" 2>/dev/null; then
  uv venv --clear --python "$python" "$venv"
  uv pip install --python "$venv/bin/python" --upgrade \
    "rknn-toolkit2==$version" 'onnx==1.16.2' 'setuptools<81'
fi
"$venv/bin/python" -c "from importlib.metadata import version; print('rknn-toolkit2', version('rknn-toolkit2'))"
