find_package(OpenCV REQUIRED COMPONENTS core imgproc)
pkg_check_modules(RGA REQUIRED IMPORTED_TARGET librga)
find_path(RKNN_INCLUDE_DIR rknn_api.h REQUIRED)
find_library(RKNN_LIBRARY rknnrt REQUIRED)

add_library(gstrknnnanotrack MODULE src/gstrknnnanotrack.cpp)
target_include_directories(gstrknnnanotrack PRIVATE "${RKNN_INCLUDE_DIR}" ${OpenCV_INCLUDE_DIRS})
target_link_libraries(gstrknnnanotrack PRIVATE
    PkgConfig::GSTREAMER PkgConfig::RGA ${OpenCV_LIBS} "${RKNN_LIBRARY}")
target_compile_options(gstrknnnanotrack PRIVATE -Wall -Wextra)
set_target_properties(gstrknnnanotrack PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "gstrknnnanotrack"
    SKIP_BUILD_RPATH TRUE)
