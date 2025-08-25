find_program(
    cpplint_exe
    NAMES cpplint
    DOC
        "cpplint: C++ style checker. Install via 'pip install cpplint', 'sudo dnf install cpplint', or 'brew install cpplint'. Required for 'cpplint' target."
)

if(cpplint_exe)
    add_custom_target(
        cpplint
        COMMAND "${cpplint_exe}" --recursive "${PROJECT_SOURCE_DIR}"
        WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
        VERBATIM
        COMMENT "running cpplint (google C++ style checker) on all sources"
        USES_TERMINAL
    )
else()
    message(
        NOTICE
        "cpplint not found. 'cpplint' target will not be available.\n"
        "install: pip install cpplint | sudo dnf install cpplint | brew install cpplint"
    )
endif()