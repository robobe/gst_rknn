add_library(gstrknnhello MODULE src/gstrknnhello.cpp)
target_link_libraries(gstrknnhello PRIVATE PkgConfig::GSTREAMER)
set_target_properties(gstrknnhello PROPERTIES PREFIX "lib" OUTPUT_NAME "gstrknnhello")
