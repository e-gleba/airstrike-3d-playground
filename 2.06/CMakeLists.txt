cmake_minimum_required(VERSION 3.28)

add_executable(as3d2_game IMPORTED GLOBAL)

set(resource_files
    as3d2_icon.ico
    data/pak0.apk
    data/pak1.apk
    data/pak2.apk)

set_target_properties(
    as3d2_game
    PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_LIST_DIR}/as3d2.exe"
               RESOURCE "${resource_files}")

add_library(
    bass
    SHARED
    IMPORTED
    GLOBAL)
set_target_properties(bass PROPERTIES IMPORTED_LOCATION
                                      "${CMAKE_CURRENT_LIST_DIR}/bass.dll")

target_link_libraries(as3d2_game INTERFACE bass)
