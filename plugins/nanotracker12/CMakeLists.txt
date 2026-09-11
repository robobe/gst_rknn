find_package(OpenCV REQUIRED COMPONENTS core imgproc)
pkg_check_modules(RGA REQUIRED IMPORTED_TARGET librga)
find_path(RKNN_INCLUDE_DIR rknn_api.h REQUIRED)
find_library(RKNN_LIBRARY rknnrt REQUIRED)

add_library(gstrknnnanotracker12 MODULE src/gstrknnnanotracker12.cpp)
target_include_directories(gstrknnnanotracker12 PRIVATE "${RKNN_INCLUDE_DIR}" ${OpenCV_INCLUDE_DIRS})
target_link_libraries(gstrknnnanotracker12 PRIVATE
    PkgConfig::GSTREAMER PkgConfig::RGA ${OpenCV_LIBS} "${RKNN_LIBRARY}")
target_compile_options(gstrknnnanotracker12 PRIVATE -Wall -Wextra)
set_target_properties(gstrknnnanotracker12 PROPERTIES PREFIX "lib" OUTPUT_NAME "gstrknnnanotracker12" SKIP_BUILD_RPATH TRUE)
