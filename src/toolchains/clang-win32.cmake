# clang-win32.cmake

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR i686)

set(LLVM_MINGW_SYSROOT "/home/egleba/Projects/llvm-mingw/i686-w64-mingw32")
get_filename_component(LLVM_MINGW_ROOT "${LLVM_MINGW_SYSROOT}" DIRECTORY)
set(LLVM_MINGW_TRIPLE "i686-w64-mingw32")

set(CMAKE_C_COMPILER   "${LLVM_MINGW_ROOT}/bin/${LLVM_MINGW_TRIPLE}-clang")
set(CMAKE_CXX_COMPILER "${LLVM_MINGW_ROOT}/bin/${LLVM_MINGW_TRIPLE}-clang++")

if(EXISTS "${LLVM_MINGW_ROOT}/bin/llvm-windres")
  set(_RC_BIN "${LLVM_MINGW_ROOT}/bin/llvm-windres")
else()
  set(_RC_BIN "${LLVM_MINGW_ROOT}/bin/${LLVM_MINGW_TRIPLE}-windres")
endif()

# absolute rc in cache, force across the tree
set(CMAKE_RC_COMPILER "${_RC_BIN}" CACHE FILEPATH "rc compiler" FORCE)

# clang target triples
set(CMAKE_C_COMPILER_TARGET   "i686-w64-windows-gnu")
set(CMAKE_CXX_COMPILER_TARGET "i686-w64-windows-gnu")

# lld
set(CMAKE_EXE_LINKER_FLAGS_INIT    "-fuse-ld=lld")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-fuse-ld=lld")

# sysroot discovery
set(CMAKE_SYSROOT "${LLVM_MINGW_SYSROOT}")
set(CMAKE_FIND_ROOT_PATH "${LLVM_MINGW_SYSROOT}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# binutils
set(CMAKE_AR     "${LLVM_MINGW_ROOT}/bin/llvm-ar")
set(CMAKE_RANLIB "${LLVM_MINGW_ROOT}/bin/llvm-ranlib")

# cross try_compile
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# rc: windres-style compile rule + headers
set(CMAKE_RC_FLAGS "-O coff -I${LLVM_MINGW_SYSROOT}/include" CACHE STRING "rc flags" FORCE)
set(CMAKE_RC_COMPILE_OBJECT
  "<CMAKE_RC_COMPILER> -O coff <DEFINES> <INCLUDES> <FLAGS> -i <SOURCE> -o <OBJECT>"
  CACHE STRING "rc compile rule" FORCE)
set(CMAKE_RC_OUTPUT_EXTENSION ".obj" CACHE STRING "rc object extension" FORCE)

# export for nested configures
set(ENV{RC}      "${_RC_BIN}")
set(ENV{RCFLAGS} "-O coff -I${LLVM_MINGW_SYSROOT}/include")

# fail fast
foreach(p IN ITEMS CMAKE_C_COMPILER CMAKE_CXX_COMPILER CMAKE_RC_COMPILER CMAKE_AR CMAKE_RANLIB)
  if(NOT EXISTS "${${p}}")
    message(FATAL_ERROR "missing: ${p} -> ${${p}}")
  endif()
endforeach()
if(NOT IS_DIRECTORY "${LLVM_MINGW_SYSROOT}")
  message(FATAL_ERROR "missing sysroot: ${LLVM_MINGW_SYSROOT}")
endif()

