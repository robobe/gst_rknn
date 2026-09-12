# gst-rknn

Cross-built C++ GStreamer plugins for the Radxa Zero 3W RKNN NPU. The initial
`rknnhello` module verifies the entire build/deploy/run path before inference
code is introduced.

## Host setup

Tested on Ubuntu 24.04:

```sh
sudo apt install cmake ninja-build pkg-config rsync openssh-client \
  gcc-12-aarch64-linux-gnu g++-12-aarch64-linux-gnu
```

Ensure `ssh radxa@radxa` works. Override the default board connection or paths
with `RADXA_HOST`, `RADXA_USER`, `RADXA_ROOT`, and `RADXA_SYSROOT`.

`sync-sysroot.sh` creates/updates `.venv-rknn` with `uv` and pins
RKNN-Toolkit2 to 2.3.2 before copying target libraries. Use its Python for all
ONNX-to-RKNN conversions: `.venv-rknn/bin/python`.

## First bring-up

```sh
./scripts/sync-sysroot.sh
cmake --preset radxa-debug
cmake --build --preset radxa-debug
./scripts/deploy.sh plugin
./scripts/remote-test.sh inspect
./scripts/remote-test.sh smoke
```

The smoke pipeline must print `Hello Radxa`. VS Code exposes the same actions
as `Radxa:` tasks; use **Radxa: build deploy test** for the normal loop.

## Adding a model plugin

Create `plugins/<model>/` with its own `CMakeLists.txt`, `README.md`, and source
files, then add it to `plugins/CMakeLists.txt`. Give its shared object a unique
`libgst<model>.so` name. CMake writes every module to the common
`build/radxa-debug/plugins/` directory, so `deploy.sh plugin` deploys all modules.
Add its name and short description to `plugin_list.md`; that catalog is deployed
to `/home/radxa/gst-rknn/plugin_list.md` with the plugin group.

Put runtime assets in `models/<model>/`. `.rknn` files are ignored by Git and
`deploy.sh models` preserves the directory tree under
`/home/radxa/gst-rknn/models/`. RKNN Runtime is intentionally not linked by
`rknnhello`; link it only in a module that calls the RKNN API.

## NanoTracker

`rknnnanotrack` is the NanoTrackV3 single-object tracker. Its source and
property reference are in `plugins/nanotracker/README.md`; run **Radxa:
NanoTracker build deploy test** to build, deploy its mixed model set, inspect
the element, and run the synthetic tracking pipeline.
