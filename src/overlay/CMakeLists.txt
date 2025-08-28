cmake_minimum_required(VERSION 3.25)

add_library(bass SHARED bass_proxy.cpp bass_proxy.def dll_main.cpp)
target_include_directories(bass PRIVATE ${CMAKE_CURRENT_LIST_DIR})

set_target_properties(
    bass
    PROPERTIES CXX_STANDARD 23
               CXX_STANDARD_REQUIRED ON
               CXX_EXTENSIONS OFF
               POSITION_INDEPENDENT_CODE ON
               PREFIX "" # no "lib" prefix
    )

# static link so we ship no extra MinGW runtimes
target_link_options(
    bass
    PRIVATE
    -static
    -s)

target_link_libraries(bass PRIVATE imgui_opengl3 dwmapi glm)

set(game_path "${CMAKE_CURRENT_LIST_DIR}/../../2.06")

add_custom_command(
    TARGET bass
    POST_BUILD
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:bass>"
        "${game_path}/bass.dll"
    COMMENT "deploying bass.dll to game dir = ${game_path}")

add_custom_command(
    TARGET bass
    POST_BUILD
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_LIST_DIR}/bass_real.dll" "${game_path}/bass_real.dll"
    COMMENT "deploying bass_real.dll to game dir = ${game_path}")

add_custom_command(
    TARGET bass
    POST_BUILD
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_LIST_DIR}/bass_real.dll" "${game_path}/_bass_real.dll"
    COMMENT "deploying _bass_real.dll to game dir = ${game_path}")
