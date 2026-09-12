pkg_check_modules(RGA REQUIRED IMPORTED_TARGET librga)
find_path(RKNN_INCLUDE_DIR rknn_api.h REQUIRED)
find_library(RKNN_LIBRARY rknnrt REQUIRED)

add_library(gstrknnyolov8 MODULE src/gstrknnyolov8.cpp)
target_include_directories(gstrknnyolov8 PRIVATE "${RKNN_INCLUDE_DIR}")
target_link_libraries(gstrknnyolov8 PRIVATE PkgConfig::GSTREAMER PkgConfig::RGA "${RKNN_LIBRARY}")
target_compile_options(gstrknnyolov8 PRIVATE -Wall -Wextra)
set_target_properties(gstrknnyolov8 PROPERTIES PREFIX "lib" OUTPUT_NAME "gstrknnyolov8" SKIP_BUILD_RPATH TRUE)
