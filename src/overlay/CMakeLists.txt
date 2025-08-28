cmake_minimum_required(VERSION 3.25)

add_library(bass_proxy_overlay SHARED bass_proxy.cpp bass_proxy.def
                                      dll_main.cpp)
target_include_directories(bass_proxy_overlay PRIVATE ${CMAKE_CURRENT_LIST_DIR})

set_target_properties(
    bass_proxy_overlay
    PROPERTIES CXX_STANDARD 23
               CXX_STANDARD_REQUIRED ON
               CXX_EXTENSIONS OFF
               POSITION_INDEPENDENT_CODE ON
               PREFIX "" # no "lib" prefix
    )

# static link so we ship no extra MinGW runtimes
target_link_options(
    bass_proxy_overlay
    PRIVATE
    -static
    -s)

target_link_libraries(bass_proxy_overlay PRIVATE imgui_opengl3 dwmapi glm)

add_custom_command(
    TARGET bass_proxy_overlay
    POST_BUILD
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different
        "$<TARGET_FILE:bass_proxy_overlay>"
        "$<TARGET_FILE_DIR:as3d2_game>/bass.dll"
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_LIST_DIR}/bass_real.dll"
        "$<TARGET_FILE_DIR:as3d2_game>/bass_real.dll"
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_LIST_DIR}/bass_real.dll"
        "$<TARGET_FILE_DIR:as3d2_game>/_bass_real.dll"
    COMMENT "deploying bass proxy libs to $<TARGET_FILE_DIR:as3d2_game>"
    VERBATIM)
