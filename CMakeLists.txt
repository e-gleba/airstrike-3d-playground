cmake_minimum_required(VERSION 3.28)

project(
    as3d_reverse_toolkit
    VERSION 1.0.0
    DESCRIPTION "Airstrike divo games reverse engineering toolkit"
    HOMEPAGE_URL "https://github.com/e-gleba/airstrike3d-tools"
    LANGUAGES C CXX)

list(
    APPEND
    CMAKE_PREFIX_PATH
    ${CMAKE_CURRENT_LIST_DIR}/cmake
    ${CMAKE_CURRENT_LIST_DIR}/cmake/utils)

list(
    APPEND
    CMAKE_FIND_ROOT_PATH
    ${CMAKE_CURRENT_LIST_DIR}/cmake
    ${CMAKE_CURRENT_LIST_DIR}/cmake/utils)

message(STATUS "CMAKE_PREFIX_PATH: ${CMAKE_PREFIX_PATH}")

find_package(warnings CONFIG REQUIRED)

find_package(clang_format CONFIG REQUIRED)
find_package(clang_tidy CONFIG REQUIRED)
find_package(clang_doc CONFIG REQUIRED)
find_package(cpplint CONFIG REQUIRED)
find_package(doxygen CONFIG REQUIRED)

find_package(cpm CONFIG REQUIRED)

add_subdirectory(src)
