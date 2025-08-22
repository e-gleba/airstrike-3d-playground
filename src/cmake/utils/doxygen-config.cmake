find_package(Doxygen)

if(DOXYGEN_FOUND)
    # Core Doxygen configuration
    set(DOXYGEN_PROJECT_NAME "${PROJECT_NAME}")
    set(DOXYGEN_PROJECT_NUMBER "${PROJECT_VERSION}")
    set(DOXYGEN_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated-docs")
    set(DOXYGEN_CREATE_SUBDIRS YES)
    set(DOXYGEN_FULL_PATH_NAMES NO)

    # Modern C++ features
    set(DOXYGEN_CLANG_ASSISTED_PARSING YES)
    set(DOXYGEN_CLANG_OPTIONS "-std=c++23;-stdlib=libc++")
    set(DOXYGEN_CPP_CLI_SUPPORT YES)
    set(DOXYGEN_MARKDOWN_SUPPORT YES)

    # Output formats
    set(DOXYGEN_GENERATE_HTML YES)
    set(DOXYGEN_HTML_OUTPUT html)
    set(DOXYGEN_GENERATE_MAN YES)
    set(DOXYGEN_MAN_OUTPUT man)

    # Content configuration
    set(DOXYGEN_EXCLUDE_PATTERNS "*/build/*" "*/third_party/*" "*/tests/*")

    set(DOXYGEN_RECURSIVE YES)
    set(DOXYGEN_EXTRACT_ALL YES)
    set(DOXYGEN_EXTRACT_PRIVATE YES)

    # Modern documentation features
    set(DOXYGEN_HTML_COLORSTYLE "dark")
    set(DOXYGEN_INTERACTIVE_SVG YES)
    set(DOXYGEN_MATHJAX_FORMAT TeX)
    set(DOXYGEN_USE_MATHJAX YES)

    doxygen_add_docs(
        doxygen
        ${PROJECT_SOURCE_DIR}
        ALL
        COMMENT "Building API documentation"
    )

    install(
        DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated-docs"
        DESTINATION "share/doc/${PROJECT_NAME}"
        COMPONENT documentation
    )
else()
    message(
        WARNING
        "Doxygen not found - documentation targets disabled\n"
        "Installation commands:\n"
        "\n"
        "  Fedora:    sudo dnf install doxygen graphviz\n"
        "  Ubuntu:    sudo apt install doxygen doxygen-latex\n"
        "  macOS:     brew install doxygen\n"
        "  Windows:   choco install doxygen.install\n"
        "\n"
        "Regenerate project after installation"
    )
endif()
