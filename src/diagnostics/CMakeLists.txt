add_library(gstroi2csv MODULE gstrknnmetacsv.cpp)
target_link_libraries(gstroi2csv PRIVATE PkgConfig::GSTREAMER)
target_compile_options(gstroi2csv PRIVATE -Wall -Wextra)
set_target_properties(gstroi2csv PROPERTIES PREFIX "lib" OUTPUT_NAME "gstroi2csv")

add_library(gstroi2udp MODULE gstroi2udp.cpp)
target_link_libraries(gstroi2udp PRIVATE PkgConfig::GSTREAMER)
target_compile_options(gstroi2udp PRIVATE -Wall -Wextra)
set_target_properties(gstroi2udp PROPERTIES PREFIX "lib" OUTPUT_NAME "gstroi2udp")
