.. _rust_install:

Install the Rust build
======================

The project ships a Rust implementation of the solver and the tool stack next to
the C++ sources. The same ``update_openEMS.sh`` entry point builds it:

.. code-block:: bash

    ./update_openEMS.sh ~/opt/openEMS --with-rust

``--with-rust`` selects the Rust workspace in the root CMake project; add
``--python`` for the Python interface and ``--disable-GUI`` on headless
machines. After the C++ subprojects are installed, the script configures the
root project, builds its ``rust-workspace`` target and installs the port over
the native names.

Installed layout
----------------

.. code-block:: text

    bin/     AppCSXCAD  ctb  hyp2mat  nf2ff  openEMS  sar_calc
    lib/     libcsxcad_matlab.so  libopenems_matlab.so
    share/   CSXCAD/matlab  openEMS/matlab

``bin/openEMS`` is the Rust solver; ``--help`` prints its version banner. The
same layout is checked by ``scripts/ci/check_cmake_install.sh`` in CI, so a
plain ``cmake --install`` and the script install agree.

Interfaces
----------

The Python packages are installed under their native import names when
``--python`` is given; the MATLAB/Octave interface uses the M-files under
``share/openEMS/matlab`` and ``share/CSXCAD/matlab`` together with the two C ABI
libraries. The migration status and the measured differences are tracked in the
repository under ``docs/migration/``.
