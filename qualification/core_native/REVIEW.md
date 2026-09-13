# Bounded Core native recipe review

Read-only inspection, 2026-09-13. Core source baseline:
`a5c3e5fa544c07d538974d3a289b19652d483848`, inspected pristine export
`/private/tmp/qb-core-pristine-source-20260913/qristal-core`.
Fresh XACC archive: SHA256
`b4569c7ca587c3a1fcbaa5e87a4606792c9a0904e2d15c5c2ef03a83b3088bb5`.
No configure, compiler, installed executable, or cloud action was run for this review.

## Can the fresh XACC satisfy Core?

There is no identified missing direct Core link library in this archive. Core
`cmake/cpp_lib.cmake` links `xacc::xacc`, `xacc::quantum_gate`, and `xacc::pauli`;
the corresponding libraries and versioned `libCppMicroServices.so.4.0.0` are
present. `bin/usResourceCompiler4`, required by Core's embedded plugin resources,
is present. QPP, XASM, STAQ, circuit optimizer, expression parser, graph, MLpack,
NLopt, QPE, IR-provider and observable-transform plugins are present. This is an
inventory finding, not proof every symbol/plugin/service is compatible with Core.

Fresh XACC was configured without Python bindings. Core's `pycore` is its own
pybind11 module, links Core/XACC C++, and initializes XACC directly
(`src/python/pybindings.cpp:19–24`); it does not import an `xacc` Python module
there. Therefore absent XACC Python bindings are not an established blocker to
the proposed QPP-only Python fixture. Python ABI, import and execution still
need native validation. Do not generalize this to Aer or other Python-dependent
backends. XACC's config advertises `1.0.0-`, not its true source identity; retain
archive and source receipts as authoritative and record actual imported paths.

## Required configure/build inputs

- CMake >=3.20; GCC >=11.4 or Clang >=16.0.6; C++20. A Fortran compiler is
  required by top-level `project(... LANGUAGES C CXX Fortran)` even when TNQVM
  is disabled. Prefer the same GNU compiler/libstdc++ family as retained XACC.
- Python 3 Interpreter **and Development**, Boost, OpenSSL, OpenMP, OpenBLAS,
  system libcurl development files; Core explicitly errors without OpenBLAS
  (`cmake/dependencies.cmake:72–77`). The eleven prepared C++ overrides and
  captured CPM script remain necessary. Observe actual selection because
  `find_package` can bypass CPM overrides.
- Use the version/Eigen-transformed Core input and explicit installed XACC at
  `/work/install-xacc`, separate `/work/install-core`, writable build directory,
  writable Python packages output and dependency cache.
- Newly identified source write: `cmake/base_config.cmake` generates
  `include/qristal/core/cmake_variables.hpp` in the **source tree**. A read-only
  Core mount fails unless this is transformed or the protocol uses a verified
  derivative source copy permitting only that generated-header change. The
  generated header records source/install paths, so record its final bytes.
- Core installs plugin symlinks into XACC's prefix via `cmake/xacc_utilities.cmake`.
  Use an audited derivative of fresh XACC, never mutate the reusable archive.
  Installation also removes selected `share`/`lib/cmake` directories within the
  Core prefix (`dependencies.cmake:432–438`); keep it isolated from XACC/system.

Concrete option set for the proposed narrow profile (paths are protocol inputs):

```text
-C /work/dependencies/overrides.cmake
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG
-DCMAKE_INSTALL_PREFIX=/work/install-core
-DCMAKE_INSTALL_LIBDIR=lib
-DXACC_DIR=/work/install-xacc
-DXACC_ROOT=/work/install-xacc
-DINSTALL_MISSING=CXX
-DWITH_TNQVM=OFF
-DWITH_TKET=OFF
-DWITH_MPI=OFF
-DENABLE_MPI_IN_DEPS=OFF
-DWITH_PROFILING=OFF
-DWITH_EXAMPLES=OFF
-DBUILD_DOCS=OFF
-DCOMPILE_FOR_LOCAL_ARCH=OFF
-DN_PROC=2
-DPython_EXECUTABLE=<explicit selected interpreter>
-DPYTHON_PACKAGES_PATH=<writable selected site-packages>
```

Do not inherit `MPI_HOME`. Ensure no `nvq++` can be discovered and verify
`WITH_CUDAQ` remains false: `dependencies.cmake:444–448` auto-enables it if the
compiler is found, overriding a plain `WITH_CUDAQ=OFF` intention. Compile with
explicit targets `core pycore xacc-plugins`, bounded parallelism, then install.
`noise` and shared dependency targets are transitive. `WITH_TESTS=OFF` is not a
working switch here: `cmake/tests.cmake` adds CITests, HardwareTests and
BraketTests unconditionally. Avoid blanket default build or blanket `ctest` for
this experiment. Installation completeness must still be checked explicitly.

## Python gate

`add_python_package` checks metadata during configure for amazon-braket-sdk,
ase, boto3, botocore, matplotlib, numpy, pytest and qiskit even for QPP-only use.
With `INSTALL_MISSING=CXX`, any absent package makes `check_missing` fail;
version mismatches only warn, so passing configure does not prove a correct
Python lock. Use the captured compatible wheelhouse with exact hashes and
record installed versions. Do not enable uncontrolled pip/network installation.
Core declares Qiskit0.46, NumPy1.26.4 and pybind11 2.12; keep this environment
separate from Integrations' Qiskit1.2 and the SDK's Python requirements. Exact
interpreter/library ABI compatibility must be checked at import time.

## Smallest meaningful installed-only fixture

Use both C++ and Python session APIs against explicitly selected `qpp`, based
on `examples/cpp/demo1/demo1.cpp` and `examples/python/quickstart.py`. Submit
OpenQASM through `session.instring`, rather than only executing raw XACC, so
this exercises Core -> compiler -> QPP -> Core result retrieval.

For each API create a fresh two-qubit session, `qn=2`, `sn=256`, `acc="qpp"`,
`noplacement=true`, `nooptimise=true`. Run (1) identity with both qubits measured
and require exactly 256 counts in `00`; (2) H on qubit0 then CX0,1 and measure
both, require exactly 256 total counts, only `00`/`11`, and both outcomes present.
Do not require exact 50:50 counts. Core C++ exposes `results()` as
`map<vector<bool>,int>`; Python exposes `results` as a property (not old nested
`out_raw`). Serialize keys deliberately and reject negative/noninteger counts.
These are four executions/two distinct fixtures, not four simulator capabilities.

Compile a separate tiny CMake consumer with `find_package(qristal_core CONFIG
REQUIRED)` and `target_link_libraries(... qristal::core)`, with only installed
prefixes and consumer source mounted. This tests exported dependency metadata;
manual link flags alone would miss broken installed CMake exports. Execute C++
and Python in fresh offline nonroot containers without original Core/XACC
source or build mounts. Python must print/check `qristal.core.__file__` under
`/work/install-core/lib/qristal`, not a historical `/opt/qb` tree. Verify linkage
for libcore, pycore and required plugins, reject unresolved libraries and old
build/image paths, then require exact fixture counts/result markers. Record
post-Core XACC manifest delta including new plugin links.

A successful result qualifies only installed Core QPP C++/Python execution in
that recorded environment. It does not qualify Aer, SparseSim, TNQVM, GPU,
commercial emulator plugins, broad upstream tests, publication or hosted use.
