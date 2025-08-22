cmake_minimum_required(VERSION 3.23)

add_library(bass SHARED bass_proxy.cpp bass_proxy.def)

set_target_properties(bass PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
    POSITION_INDEPENDENT_CODE ON
    PREFIX ""            # no "lib" prefix
    WINDOWS_EXPORT_ALL_SYMBOLS OFF  # we rely on .def
)

# static link so we ship no extra MinGW runtimes
target_link_options(bass PRIVATE -static -s)

target_link_libraries(bass PRIVATE imgui_opengl3 dwmapi)

set(STEAM_PREFIX_PATH "/home/e_gleba/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/2180100/pfx/drive_c/2.06")

add_custom_command(TARGET bass POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "$<TARGET_FILE:bass>"
        "${STEAM_PREFIX_PATH}/bass.dll"
        COMMENT "deploying bass.dll to steam proton prefix = ${STEAM_PREFIX_PATH}"
)