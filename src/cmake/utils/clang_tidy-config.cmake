find_program(
    clang_tidy_exe
    NAMES clang-tidy
    DOC
        "clang-tidy: clang-based C++ linter. Install: 'sudo dnf install clang-tools-extra', 'sudo apt install clang-tidy', 'brew install llvm', or 'choco install llvm'. Required for 'clang_tidy' target."
)

if(clang_tidy_exe)
    add_custom_target(
        clang_tidy
        COMMAND
            "${clang_tidy_exe}" "${PROJECT_SOURCE_DIR}/**/*.{cpp,cxx,hpp,hxx}"
            -- -std=c++20
        WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
        VERBATIM
        COMMENT "running clang-tidy (static analysis and lint) on all sources"
        USES_TERMINAL
    )
else()
    message(
        NOTICE
        "clang-tidy not found. 'clang_tidy' target will not be available.\n"
        "install: sudo dnf install clang-tools-extra | sudo apt install clang-tidy | brew install llvm | choco install llvm"
    )
endif()