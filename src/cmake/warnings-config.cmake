add_library(warnings INTERFACE)

target_compile_options(
    warnings
    INTERFACE
        "$<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion
              >"
        "$<$<CXX_COMPILER_ID:MSVC>:/W4;/wd4100;/wd4505
    >"
)

set_target_properties(warnings PROPERTIES CMAKE_COMPILE_WARNINGS_AS_ERROR TRUE)

target_compile_options(
    warnings
    INTERFACE
        # Common warnings for GCC/Clang in all configs
        "$<$<COMPILE_LANG_AND_ID:CXX,GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion;-Wno-unused-function>"
        "$<$<COMPILE_LANG_AND_ID:C,GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion;-Wno-unused-function>"
        # MSVC basic warnings (equivalent to /W4)
        "$<$<CXX_COMPILER_ID:MSVC>:/W4>"
        "$<$<C_COMPILER_ID:MSVC>:/W4>"
        # Debug config specific
        "$<$<AND:$<CONFIG:Debug>,$<COMPILE_LANG_AND_ID:C,CXX,GNU,Clang,AppleClang>>:-Og;-g;-fsanitize=address,undefined>"
        # Release config specific
        "$<$<AND:$<CONFIG:Release>,$<COMPILE_LANG_AND_ID:C,CXX,GNU,Clang,AppleClang>>:-Ofast;-march=native;-DNDEBUG>"
        "$<$<AND:$<CONFIG:Release>,$<CXX_COMPILER_ID:MSVC>>:/O2;/fp:fast>"
        # Warnings as errors
        "$<$<CXX_COMPILER_ID:MSVC>:/WX>"
        "$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Werror>"
)
