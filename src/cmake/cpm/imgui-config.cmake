# ImGui
cpmaddpackage(
    NAME
    imgui
    VERSION
    1.91.9
    GITHUB_REPOSITORY
    ocornut/imgui
    DOWNLOAD_ONLY
    TRUE
)

add_library(imgui STATIC)

target_sources(
    imgui
    PRIVATE
        ${imgui_SOURCE_DIR}/imgui.cpp
        ${imgui_SOURCE_DIR}/imgui_demo.cpp
        ${imgui_SOURCE_DIR}/imgui_draw.cpp
        ${imgui_SOURCE_DIR}/imgui_tables.cpp
        ${imgui_SOURCE_DIR}/imgui_widgets.cpp
        ${imgui_SOURCE_DIR}/misc/cpp/imgui_stdlib.cpp
        ${imgui_SOURCE_DIR}/misc/freetype/imgui_freetype.cpp
)

target_include_directories(
    imgui
    SYSTEM
    PUBLIC
        ${imgui_SOURCE_DIR}
        ${imgui_SOURCE_DIR}/misc/cpp
        ${imgui_SOURCE_DIR}/misc/freetype
)

target_link_libraries(imgui PRIVATE freetype)

# Adding backend implementations
#
# OpenGL installation commands:
#   - Windows:   vcpkg install opengl --triplet=x64-windows
#   - Fedora:    sudo dnf install mesa-libGL-devel mesa-libGLU-devel
#   - Arch:      sudo pacman -S mesa glu
#   - Ubuntu:    sudo apt-get install libgl1-mesa-dev libglu1-mesa-dev

add_library(imgui_opengl2 STATIC)

target_sources(
    imgui_opengl2
    PRIVATE
    ${imgui_SOURCE_DIR}/backends/imgui_impl_win32.cpp
            ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl2.cpp
)

target_link_libraries(imgui_opengl2 PUBLIC imgui glad opengl32)