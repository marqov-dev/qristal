# Native Core stages (unexecuted protocol)

`stages.sh` selects one explicit stage. It is not an orchestrator, sandbox or
permission to launch compute. The parent guest owns frozen-input verification,
container mounts and resource/time bounds, source/install snapshots, logs,
native validation, artifact retention and cleanup. Each stage must execute as
non-root in a networkless CPU container with no credentials, read-only `/inputs`
and bounded `/tmp`. Only the intended fresh `/work` outputs may be writable.

Paths expected by the recipe:

| Path | Contents |
| --- | --- |
| `/inputs/core` | Verified prepared Core source, never writable |
| `/inputs/antlr` | `recipe.py`, `inputs.json`, `build.sh`, source tar and two exact tool wheels |
| `/inputs/python/core.json` | Retained manifest of exactly 50 acquired Core wheels |
| `/inputs/python/wheels` | Those 50 exact wheel filenames, no extras |
| `/work/source-core` | New manifest-bound copy of prepared Core source |
| `/work/core-dependencies` | Verified prepared overrides, patched Eigen and 11 sources, captured CPM cache |
| `/work/install-xacc` | Newly extracted verified XACC installation; a disposable derivative |
| `/work/antlr`, `/work/python-core` | Separate new ANTLR build output and Core Python venv |
| `/work/build-core`, `/work/install-core` | New CMake build tree and final installation |

Run stages in order: `antlr`, `python`, `configure`, `build`, `install`. Use one
bounded container call per stage so the parent can retain each exit code and
complete log. Suggested starting bounds are 120, 180, 300, 900 and 120 seconds;
the parent must fit these within the existing VM observation/cleanup deadline.
Build results remain uncertain; exhausting a bound is evidence, not permission
to expand it silently.

## Selected source behavior

These commands come from locked Core
`a5c3e5fa544c07d538974d3a289b19652d483848`, not inferred option names:

- `base_config.cmake` parses `INSTALL_MISSING=CXX` into C++ acquisition allowed
  and Python installation disabled. Its GNU minimum is 11.4.0. The project
  declares C, C++ and Fortran even with TNQVM disabled. The builder therefore
  needs GCC/G++11.4+, gfortran, CMake3.20+, matching Python3.10 interpreter and
  development headers, OpenMP, system Boost, OpenSSL, OpenBLAS and curl development
  files. Record actual installed system versions; they are not new source pins.
- `base_config.cmake:105` generates `include/qristal/core/cmake_variables.hpp`
  **inside the source directory**. The parent must copy `/inputs/core` to a new
  `/work/source-core` before configure and permit only that generated-header
  delta in the resulting source manifest. Unexpected source writes fail
  qualification. Existing Core version/Eigen transformations remain identified.
- `dependencies.cmake` selects the eleven CPM overrides but can discover system
  packages first. `--debug-find` and CMakeCache/selected paths must be retained
  and independently checked; offline configure succeeding does not prove which
  sources were used. Network isolation is authoritative if a nested fetch is
  attempted. The disconnected FetchContent flags are additional controls.
- `examples.cmake:37` declares `WITH_EXAMPLES`; the recipe disables it explicitly.
  `tests.cmake` declares its CPU/hardware/Braket targets unconditionally, with no
  blanket `BUILD_TESTING=OFF` switch. Building only the actual `core`, `pycore`,
  `xacc-plugins` targets avoids requesting those tests. It does not claim they
  passed. No full Decoder is added.
- CUDA-Q detection is based on finding `nvq++` and can override a false variable,
  so configure explicitly refuses a builder containing that executable.
- `xacc_utilities.cmake:132-153` installs Core plugin libraries into Core's prefix
  and creates **absolute** links in XACC's plugin directory. The XACC prefix must
  be the disposable verified derivative, never the retained original artifact.
  Parent must verify allowed plugin-link additions, final targets and unchanged
  original XACC file bytes. `cmake --install` may not fail for every nested
  `execute_process` error, so its exit status is insufficient by itself.
- `py_packages_path.cmake` writes a `.pth` to the explicit bounded
  `/work/install-core/python-site`. Installed-only validation must deliberately
  process that site directory (e.g. `site.addsitedir`), not assume that adding a
  directory to `PYTHONPATH` processes its `.pth` files.

## Python acquisition boundary

ANTLR's source and build tools are verified by its prepared recipe before its
native build. Before installing the Core venv, every acquired wheel is checked
against its exact file/length/SHA manifest and the new ANTLR wheel is checked
against metadata and complete RECORD hashes. A generated requirements file
names only those local paths and hashes. Pip uses `--no-index --no-deps
--require-hashes`; `pip check` must pass before CMake. Pip itself comes from the
pinned builder's ensurepip and its version is recorded. It must not acquire or
upgrade packages during configure. Qiskit0.46 belongs to this Core environment;
the Integrations Qiskit1.2 environment is separate.

Not yet established: configure success, actual dependency selections, ABI
compatibility, installed-only fixtures, reproducibility, publication or hosted
admission. These stage recipes do not change any existing qualification claim.
