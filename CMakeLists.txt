
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

message(STATUS "Build AppCSXCAD: " ${BUILD_APPCSXCAD})
message(STATUS "Build Rust extensions: " ${BUILD_RUST})

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

# build Rust extensions (all submodule Rust ports)
if (${BUILD_RUST})
    # build fparser-rs
    ExternalProject_Add( fparser-rs
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/fparser/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/fparser/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build csxcad-core
    ExternalProject_Add( csxcad-core
      DEPENDS     fparser-rs
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/CSXCAD/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/CSXCAD/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build csxcad-py (Python bindings)
    ExternalProject_Add( csxcad-py
      DEPENDS     csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/CSXCAD/rust-py
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo maturin build --release --manifest-path ${PROJECT_SOURCE_DIR}/CSXCAD/rust-py/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build csxcad-matlab (C ABI shared library for MATLAB/Octave MEX)
    ExternalProject_Add( csxcad-matlab
      DEPENDS     csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/CSXCAD/rust-matlab
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/CSXCAD/rust-matlab/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build openems-core
    ExternalProject_Add( openems-core
      DEPENDS     csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/openEMS/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/openEMS/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build openems-py (Python bindings via maturin)
    ExternalProject_Add( openems-py
      DEPENDS     openems-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/openEMS/rust-py
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo maturin build --release --manifest-path ${PROJECT_SOURCE_DIR}/openEMS/rust-py/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build openems-matlab (C ABI shared library for MATLAB/Octave MEX)
    ExternalProject_Add( openems-matlab
      DEPENDS     openems-core csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/openEMS/rust-matlab
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/openEMS/rust-matlab/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build openems-cli (command-line interface)
    ExternalProject_Add( openems-cli
      DEPENDS     openems-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/openEMS/rust-cli
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/openEMS/rust-cli/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build qcsxcad-core
    ExternalProject_Add( qcsxcad-core
      DEPENDS     csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/QCSXCAD/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/QCSXCAD/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build qcsxcad-egui (QCSXCAD GUI: egui + wgpu)
    ExternalProject_Add( qcsxcad-egui
      DEPENDS     qcsxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/QCSXCAD/rust-egui
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/QCSXCAD/rust-egui/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build appcsxcad (AppCSXCAD binary)
    ExternalProject_Add( appcsxcad
      DEPENDS     qcsxcad-egui
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/AppCSXCAD/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/AppCSXCAD/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build hyp2mat-rs
    ExternalProject_Add( hyp2mat-rs
      DEPENDS     csxcad-core
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/hyp2mat/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/hyp2mat/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )

    # build ctb-rs (Circuit Toolbox)
    ExternalProject_Add( ctb-rs
      SOURCE_DIR  ${PROJECT_SOURCE_DIR}/CTB/rust
      CONFIGURE_COMMAND ""
      BUILD_COMMAND ${CMAKE_COMMAND} -E env CARGO_HOME=${CMAKE_INSTALL_PREFIX}/cargo cargo build --release --manifest-path ${PROJECT_SOURCE_DIR}/CTB/rust/Cargo.toml
      BUILD_IN_SOURCE 1
      INSTALL_COMMAND ""
    )
endif()
