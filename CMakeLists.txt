
## usage: cmake -DCMAKE_INSTALL_PREFIX=<install/path> .
## use -DBUILD_APPCSXCAD=NO to not build QCSXCAD and AppCSXCAD
## use -DBUILD_RUST=YES to build Rust extensions (openems-core, openems-py, hyp2mat-rs)

# In CMake 4, 3.10 is deprecated and 3.5 has been removed.
# use 3.0...3.10 so all of these versions are acceptable as min. version.
# https://cmake.org/cmake/help/latest/command/cmake_minimum_required.html
cmake_minimum_required(VERSION 3.0...3.10)

PROJECT(openEMS-Project CXX)

if (CMAKE_TOOLCHAIN_FILE)
    message(STATUS "Using CMAKE_TOOLCHAIN_FILE: " ${CMAKE_TOOLCHAIN_FILE})
endif()

if (CMAKE_INSTALL_PREFIX)
    message(STATUS "Using CMAKE_INSTALL_PREFIX: " ${CMAKE_INSTALL_PREFIX})
endif()

if (NOT DEFINED BUILD_APPCSXCAD)
    set(BUILD_APPCSXCAD "YES")
endif()

if (NOT DEFINED BUILD_RUST)
    set(BUILD_RUST "NO")
endif()

if (NOT DEFINED BUILD_RUST_PYTHON)
    set(BUILD_RUST_PYTHON "NO")
endif()

message(STATUS "Build AppCSXCAD: " ${BUILD_APPCSXCAD})
message(STATUS "Build Rust extensions: " ${BUILD_RUST})
message(STATUS "Build Rust Python wheels: " ${BUILD_RUST_PYTHON})

IF(EXISTS ${PROJECT_SOURCE_DIR}/localConfig.cmake)
   message(STATUS "include local config" )
   include(${PROJECT_SOURCE_DIR}/localConfig.cmake)
ENDIF()

include(ExternalProject)

# build fparser
ExternalProject_Add( fparser
  SOURCE_DIR  ${PROJECT_SOURCE_DIR}/fparser
  CMAKE_ARGS -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
)

# build CSXCAD
ExternalProject_Add( CSXCAD 
  DEPENDS     fparser
  SOURCE_DIR  ${PROJECT_SOURCE_DIR}/CSXCAD
  CMAKE_ARGS  -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DFPARSER_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
)

# build openEMS
ExternalProject_Add( openEMS
  DEPENDS     fparser CSXCAD
  SOURCE_DIR  ${PROJECT_SOURCE_DIR}/openEMS
  CMAKE_ARGS  -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DFPARSER_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DCSXCAD_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
)

if (${BUILD_APPCSXCAD})
    # build QCSXCAD
    ExternalProject_Add( QCSXCAD
    DEPENDS     CSXCAD
    SOURCE_DIR  ${PROJECT_SOURCE_DIR}/QCSXCAD
    CMAKE_ARGS  -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DCSXCAD_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
    )

    # build AppCSXCAD
    ExternalProject_Add( AppCSXCAD
    DEPENDS     QCSXCAD
    SOURCE_DIR  ${PROJECT_SOURCE_DIR}/AppCSXCAD
    CMAKE_ARGS  -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DCSXCAD_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DQCSXCAD_ROOT_DIR=${CMAKE_INSTALL_PREFIX} -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
    )
endif()

# ---------------------------------------------------------------------------
# Rust workspace
#
# All submodule crates are members of the root Cargo workspace, so one cargo
# invocation builds them with a shared target directory. Python bindings and
# wheels are only built with -DBUILD_RUST_PYTHON=YES (native --python).
# ---------------------------------------------------------------------------
if (${BUILD_RUST})
    find_program(CARGO_EXECUTABLE cargo REQUIRED)
    set(RUST_TARGET_DIR "${CMAKE_BINARY_DIR}/rust-target" CACHE PATH "Cargo target directory")
    set(RUST_CARGO_HOME "" CACHE PATH "Optional CARGO_HOME for the Rust build")
    if (RUST_CARGO_HOME)
        set(RUST_ENV ${CMAKE_COMMAND} -E env CARGO_HOME=${RUST_CARGO_HOME})
    else()
        set(RUST_ENV ${CMAKE_COMMAND} -E env)
    endif()

    set(RUST_CARGO_ARGS build --release --target-dir "${RUST_TARGET_DIR}")
    if (BUILD_RUST_PYTHON)
        # The PyO3 crates need a compatible Python interpreter; the native
        # build also gates them behind --python.
        set(RUST_CARGO_ARGS build --workspace --release --target-dir "${RUST_TARGET_DIR}")
    endif()

    add_custom_target(rust-workspace ALL
        COMMAND ${RUST_ENV} ${CARGO_EXECUTABLE} ${RUST_CARGO_ARGS}
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        COMMENT "Building the Rust workspace"
        VERBATIM
    )

    if (BUILD_RUST_PYTHON)
        find_program(MATURIN_EXECUTABLE maturin REQUIRED)
        set(RUST_PYTHON "" CACHE FILEPATH "Python interpreter used for the wheels")
        set(RUST_PYTHON_ARG "")
        if (RUST_PYTHON)
            set(RUST_PYTHON_ARG --interpreter ${RUST_PYTHON})
        endif()
        add_custom_target(rust-wheels ALL
            COMMAND ${RUST_ENV} ${MATURIN_EXECUTABLE} build --release ${RUST_PYTHON_ARG}
                    --manifest-path ${PROJECT_SOURCE_DIR}/CSXCAD/rust-py/Cargo.toml
                    --out ${CMAKE_BINARY_DIR}/wheels
            COMMAND ${RUST_ENV} ${MATURIN_EXECUTABLE} build --release ${RUST_PYTHON_ARG}
                    --manifest-path ${PROJECT_SOURCE_DIR}/openEMS/rust-py/Cargo.toml
                    --out ${CMAKE_BINARY_DIR}/wheels
            DEPENDS rust-workspace
            COMMENT "Building the Python wheels"
            VERBATIM
        )
        install(DIRECTORY ${CMAKE_BINARY_DIR}/wheels/ DESTINATION share/openEMS/python/wheels)
    endif()

    if (WIN32)
        set(RUST_SHARED_PREFIX "")
        set(RUST_SHARED_SUFFIX ".dll")
    elseif (APPLE)
        set(RUST_SHARED_PREFIX "lib")
        set(RUST_SHARED_SUFFIX ".dylib")
    else()
        set(RUST_SHARED_PREFIX "lib")
        set(RUST_SHARED_SUFFIX ".so")
    endif()

    # Executables: the native names are part of the user-facing contract.
    install(PROGRAMS ${RUST_TARGET_DIR}/release/openems-cli${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin RENAME openEMS${CMAKE_EXECUTABLE_SUFFIX})
    install(PROGRAMS ${RUST_TARGET_DIR}/release/appcsxcad${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin RENAME AppCSXCAD${CMAKE_EXECUTABLE_SUFFIX})
    install(PROGRAMS ${RUST_TARGET_DIR}/release/hyp2mat${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin)
    # The native install ships these three commands next to openEMS.
    install(PROGRAMS ${RUST_TARGET_DIR}/release/nf2ff-cli${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin RENAME nf2ff${CMAKE_EXECUTABLE_SUFFIX})
    install(PROGRAMS ${RUST_TARGET_DIR}/release/sar-cli${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin RENAME sar_calc${CMAKE_EXECUTABLE_SUFFIX})
    # RM-116: the CTB command line (info/convert/renorm) for MATLAB/Octave.
    install(PROGRAMS ${RUST_TARGET_DIR}/release/ctb${CMAKE_EXECUTABLE_SUFFIX}
            DESTINATION bin)

    # C ABI libraries consumed by the MATLAB/Octave MEX layer.
    install(FILES
            ${RUST_TARGET_DIR}/release/${RUST_SHARED_PREFIX}csxcad_matlab${RUST_SHARED_SUFFIX}
            ${RUST_TARGET_DIR}/release/${RUST_SHARED_PREFIX}openems_matlab${RUST_SHARED_SUFFIX}
            DESTINATION lib)

    # Scripting layers keep the native install layout.
    install(DIRECTORY ${PROJECT_SOURCE_DIR}/openEMS/matlab DESTINATION share/openEMS)
    install(DIRECTORY ${PROJECT_SOURCE_DIR}/CSXCAD/matlab DESTINATION share/CSXCAD)
    install(DIRECTORY ${PROJECT_SOURCE_DIR}/openEMS/python/Tutorials
            DESTINATION share/openEMS/python)
endif()