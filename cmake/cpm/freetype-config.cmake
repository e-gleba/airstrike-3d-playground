cpmaddpackage(
    NAME freetype
    GITHUB_REPOSITORY aseprite/freetype2
    GIT_TAG VER-2-10-0
    VERSION 2.10.0
)

set_target_properties(
    freetype
    PROPERTIES
        CMAKE_RC_FLAGS "$<$<C_COMPILER_ID:MSVC>:${CMAKE_RC_FLAGS} /c65001>"
)

target_compile_options(freetype PRIVATE "$<$<C_COMPILER_ID:MSVC>:/c65001>")
# Or, if you want to append, use a generator expression to only apply for MSVC:
# target_compile_options(freetype PRIVATE "$<$<C_COMPILER_ID:MSVC>:${CMAKE_CXX_FLAGS} /c65001>")

target_compile_definitions(freetype PRIVATE "$<$<C_COMPILER_ID:MSVC>:_UNICODE>")

add_library(Freetype::Freetype ALIAS freetype)
set(FREETYPE_FOUND TRUE)
set(FREETYPE_INCLUDE_DIRS "")
set(FREETYPE_LIBRARIES Freetype::Freetype)
