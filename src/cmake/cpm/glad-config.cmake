cpmaddpackage(
    NAME
    glad
    GITHUB_REPOSITORY
    Dav1dde/glad
    GIT_TAG
    v0.1.33
    OPTIONS
    "PROFILE     core"
    "API         gl=2.1"       # or gl=3.0,gl=3.3 etc
    "GENERATE_CMAKE_CONFIG ON"  # exports glad-config.cmake
    "SPECIFY_LOADER   ON"      # build the loader
)


