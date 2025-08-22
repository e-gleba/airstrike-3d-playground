cmake_minimum_required(VERSION 3.16)
project(bass_proxy LANGUAGES C)

# Build a 32-bit proxy DLL
add_library(bass SHARED bass_proxy.c bass_proxy.def)

# produce “bass.dll” with no lib prefix
set_target_properties(bass PROPERTIES OUTPUT_NAME "bass" PREFIX "")

# static link so we ship no extra MinGW runtimes
target_link_options(bass PRIVATE -static -s)

