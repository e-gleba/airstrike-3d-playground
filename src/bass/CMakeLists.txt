cmake_minimum_required(VERSION 3.16)
project(bass_stub LANGUAGES C CXX)

add_library(bass SHARED bass_stub.cpp bass_stub.def)
set_target_properties(bass PROPERTIES OUTPUT_NAME "bass" PREFIX "")
target_link_options(bass PRIVATE -static -s)   # <─ static, strip

