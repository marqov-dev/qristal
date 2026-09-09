# Installed public CPU runtime qualification

This closes the build-tree dependency gap for the selected CPU runtime. Tests run with **no Core/XACC source trees, build directories, dependency source cache, QB image or commercial installation mounted**. The only product mounts are installed Core/XACC prefixes, installed Python dependencies and the copy-installed Integrations module. Test fixtures and a writable consumer-output directory are separate. Runtime networking is disabled, environment variables are cleared, and no LD_LIBRARY_PATH workaround is used.

## Recorded result

* 8 ideal Core CPU fixtures pass, including QASM input, optimization and result retrieval.
* 10 native Aer noise fixtures pass against analytical expectations.
* 16 Qiskit 1.2 V1 sampler/estimator checks pass on qpp and Aer.
* 9 deterministic simplified-decoder fixtures pass on qpp, Aer and sparse-sim. A small C++ consumer is compiled against installed XACC headers/libraries and loads the installed Decoder plugin.
* An independent `find_package(qristal_core)` consumer configures, compiles and runs using installed Core headers, libraries and dependencies.
* All 39 installed ELF shared libraries resolve their dependencies; install symlinks resolve within the two installed prefixes. The runtime loader maps contain installed libraries, not build-tree libraries.

Two defects were exposed:

1. The XACC configuration installed unnecessary GoogleTest shared libraries with unresolved standalone linkage. The CPU recipe now sets `INSTALL_GTEST=OFF`. Both install directories were recreated empty before repeating installation and qualification.
2. Core exported its bundled Eigen from the source tree but did not install it. Core PR #2 installs that copy and exports the installed path. The before-fix CMake failure and after-fix consumer result are recorded separately in that PR and here.

No runtime algorithm changes were needed in this stage. Existing qualified compilation outputs were reused; additional Core runtime targets were built (178.5 seconds) before the clean CMake installations. This stage is **not another from-scratch compilation claim**. The preceding CPU/noise evidence records that separate fresh build.

## Exact source boundary

* Qualification baseline: `ada611e1f9f4f8828d7c80417c853c72da558bb6`, plus this qualification change.
* Core: merged baseline `55fa21f502e47dd486ac624514af0a7983db2cab` plus packaging fix `d393cf0e118ffa631e61f36148a41c028685ddea` ([Core PR #2](https://github.com/marqov-dev/qristal-core/pull/2)). This source lock depends on that reviewable fix; it does not imply the PR has merged.
* Decoder: merged `13bb8f80f98bd259196834a13817c23ec02480e6`.
* Integrations: merged `16e4941ef5ad8476ad971a366ecce91e5ea5bd45`.
* Public XACC: `d1edaa7ae53edc7e335f46d33160f93d6020aaa3` plus the recorded CPU/ACZ patches, including its public qpe plugin for the `C-U` service.

The source lock records public submodules and the Boost archive checksum. Ubuntu 22.04 base/toolchain digests, dependency versions, commands, mount restrictions, before-fix failures and final outputs are retained under `../evidence/2026-09-09-installed`. The selected toolchain uses GCC 11.4 and Python 3.10.12, Linux amd64 under emulation. Containers are restricted to 2 CPUs, 4 GiB including swap and 256 PIDs. Apt package versions are recorded, not snapshot-pinned.

## Reproduce in an isolated workspace

Use the public preparation/toolchain/Core CPU steps in the parent README. `prepare_sources.py` now also acquires the pinned Decoder and Integrations sources. Use a fresh dedicated workspace; it refuses unexpected existing source revisions.

To reproduce the joint Core/Decoder source-tree build used for installation, create `/work/decoder-project.cmake` in the container workspace with:

```cmake
set(SKIP_FIND_CORE ON)
set(qristal_core_FOUND ON)
set(qristal_core_DIR /work/qristal-core)
add_subdirectory(/work/qristal-decoder /work/build-core/decoder)
```

Append `include(/work/decoder-project.cmake)` to **only the disposable Core checkout's** CMakeLists.txt. This is a qualification harness, not a Core product change. Then:

```sh
python3 qristal/qualification/run_stage.py core-configure
python3 qristal/qualification/run_stage.py runtime-build
python3 qristal/qualification/run_stage.py core-install
```

`core-install` includes Decoder through that harness. The installer writes Python package information inside the isolated install prefix. It does not install into the host's Python environment. XACC must have been configured with INSTALL_GTEST=OFF before its normal install step. Start with empty Core/XACC installation prefixes; disabling an install option does not remove artifacts from an earlier install.

The Qiskit adapter has no packaged distribution in this qualification. Install its pinned Python dependencies separately into `/work/integration-deps` using `qristal-integrations/qualification/requirements-cpu.txt`; use a dedicated workspace TMPDIR if the 256 MiB tmpfs is too small for pip. Do not mix that Qiskit 1.2 environment with the Core build's Qiskit 0.46 environment. Public dependency acquisition is the only networked step. `prepare_installed.py` copy-installs the adapter module and its license into `install-integrations`, and prepares tests from the pinned repositories:

```sh
python3 qristal/qualification/prepare_installed.py
python3 qristal/qualification/run_installed.py core
python3 qristal/qualification/run_installed.py noise
python3 qristal/qualification/run_installed.py integration
python3 qristal/qualification/run_installed.py decoder-build
python3 qristal/qualification/run_installed.py decoder
python3 qristal/qualification/run_installed.py consumer-configure
python3 qristal/qualification/run_installed.py consumer-build
python3 qristal/qualification/run_installed.py consumer
python3 qristal/qualification/run_installed.py audit
```

The installed-only launcher never mounts the workspace root. It checks that source/build/vendor directories are absent, imports Core from its installed location, and records loaded shared-library paths. It mounts installed prefixes read-only and runs from an empty temporary home. The C++ consumer compile is also isolated from Core/XACC sources. Each stage records its result independently; all stages must succeed.

## Limits and next boundary

This qualifies fixed prefixes `/work/install-core` and `/work/install-xacc` on the recorded Ubuntu/Python ABI. It is not a relocatable wheel, a minimal production container, a multi-architecture package, or a deployment. The runtime still uses the public toolchain image's system libraries. Core install rules include additional plugins such as AWS/VQE; loading/linking those libraries is not functional qualification of those capabilities. No remote or paid jobs ran.

Full quantum-decoder execution, GPU/tensor backends, commercial Emulator/vQPU, Qiskit V2, general Qiskit measurement/option semantics and application-scale performance remain outside this result. The next bounded task is to turn the qualified CPU prefixes into a pinned execution image with a capability allowlist, then connect it through the platform's agreed isolated execution contract. Neither is an established dependency of the current SDK/compiler release work.
