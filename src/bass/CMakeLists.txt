cmake_minimum_required(VERSION 3.23)
project(bass_proxy LANGUAGES C CXX)

add_library(bass SHARED bass_proxy.cpp bass_proxy.def)

set_target_properties(bass PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
    POSITION_INDEPENDENT_CODE ON
    OUTPUT_NAME "bass"   # produce bass.dll
    PREFIX ""            # no "lib" prefix
    WINDOWS_EXPORT_ALL_SYMBOLS OFF  # we rely on .def
)

# static link so we ship no extra MinGW runtimes
target_link_options(bass PRIVATE -static -s)

target_link_libraries(bass PRIVATE imgui_opengl2 dwmapi)
