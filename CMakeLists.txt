cmake_minimum_required(VERSION 3.24)
project(gst_rknn VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
# Every model module produces a discoverable GStreamer plugin in one place.
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/plugins")

find_package(PkgConfig REQUIRED)
pkg_check_modules(GSTREAMER REQUIRED IMPORTED_TARGET
    gstreamer-1.0 gstreamer-base-1.0 gstreamer-video-1.0)
add_subdirectory(plugins)
add_subdirectory(src/diagnostics)
