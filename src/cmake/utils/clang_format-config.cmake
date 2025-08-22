find_program(
    clang_format_exe
    NAMES clang-format
    DOC
        "clang-format: automatic C/C++ code formatter. Install: 'sudo dnf install clang-tools-extra', 'sudo apt install clang-format', 'brew install llvm', or 'choco install llvm'. Required for 'clang_format' target."
)

if(clang_format_exe)
    add_custom_target(
        clang_format
        COMMAND
            "${clang_format_exe}" -i
            "${PROJECT_SOURCE_DIR}/**/*.{cpp,cxx,hpp,hxx}"
        WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
        VERBATIM
        COMMENT
            "running clang-format (automatic code style formatting) on all sources"
        USES_TERMINAL
    )
else()
    message(
        NOTICE
        "clang-format not found. 'clang_format' target will not be available.\n"
        "install: sudo dnf install clang-tools-extra | sudo apt install clang-format | brew install llvm | choco install llvm"
    )
endif()