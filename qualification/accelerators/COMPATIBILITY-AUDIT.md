# Remaining bridge and tensor-network compatibility audit

Read-only inspection of clean Core checkout
a5c3e5fa544c07d538974d3a289b19652d483848. No compilation or runtime probe
was performed for this audit. Qristal qualification baseline is merged PR18.

## Core/CUDA-Q bridge

[dependencies.cmake:443](https://github.com/marqov-dev/qristal-core/blob/a5c3e5fa544c07d538974d3a289b19652d483848/cmake/dependencies.cmake#L443)
finds nvq++ and derives include/lib directories from its parent installation.
Finding the compiler automatically enables WITH_CUDAQ; this block does not check
a compatible CUDA-Q version. Compiler discovery alone is not ABI qualification.

[cpp_lib.cmake:159](https://github.com/marqov-dev/qristal-core/blob/a5c3e5fa544c07d538974d3a289b19652d483848/cmake/cpp_lib.cmake#L159)
requires C++20 and named libraries including cudaq-builder, cudaq-em-default,
cudaq-platform-default and cudaq-spin. The next compatibility check must compare
these exact requirements to the selected released runtime, not merely check that
Python imports cudaq.

[sim_pool.cpp:42](https://github.com/marqov-dev/qristal-core/blob/a5c3e5fa544c07d538974d3a289b19652d483848/src/cudaq/sim_pool.cpp#L42)
locates a loaded libcudaq directory, scans libnvqir-* libraries, constructs
cudaq: names and dynamically loads simulator objects. Library layout, exported
symbols and C++ interfaces are therefore explicit integration dependencies.
No incompatibility with CUDA-Q0.15 is proved solely by this source inspection.

[tests.cmake:160](https://github.com/marqov-dev/qristal-core/blob/a5c3e5fa544c07d538974d3a289b19652d483848/cmake/tests.cmake#L160)
already defines CudaqCITests. GPU test sections additionally require a discovered
CUDA compiler and BUILD_TESTS_WITHOUT_GPU being false. A passing test binary
without those sections would not qualify the GPU bridge.

Smallest later probe: inventory the selected release's required headers/libraries,
compile the existing Core bridge and CudaqCITests in isolation, then explicitly
record enabled tests and target. Run a CPU target first; use A10G only after
compile/CPU compatibility passes. Retain failure stages and avoid rebuilding a
complete CUDA-Q distribution unless the inventory establishes that it is needed.

## ExaTN/TNQVM

[dependencies.cmake:336](https://github.com/marqov-dev/qristal-core/blob/a5c3e5fa544c07d538974d3a289b19652d483848/cmake/dependencies.cmake#L336)
gates this path on WITH_TNQVM. The selected CPU qualification disabled it.
The block pins QB GitLab ExaTN 1a2e8944 and TNQVM 8d8463ad, uses Fortran and
OpenBLAS, controls MPI, and disables dependency tests. It also explicitly handles
OpenMP runtime flags. These are concrete build requirements, not GPU requirements.

A public-source replacement must select and lock available upstream commits;
changing repository URLs while retaining unavailable fork hashes is insufficient.
Compare XACC/plugin and ExaTN interfaces before proposing compatibility patches.
Enable and retain relevant upstream tests in the isolated probe, then load the
installed plugin from a source-free prefix and run phase-sensitive/Bell/GHZ
fixtures with explicit truncation settings. Build success or plugin discovery
alone is insufficient.

This audit does not establish whether unavailable fork changes are required.
Aer MPS remains the demonstrated alternative CPU tensor-network capability.
There is no evidence-based need to place TNQVM reconstruction on the platform
release path.

## Decision gate

Keep both original paths experimental/unadvertised until their own native checks
pass. If compatibility costs outweigh a concrete user need, maintain the tested
standalone CUDA-Q and Aer alternatives and document the unsupported legacy names.
Do not equate either alternative with proprietary qb_mps, commercial Emulator,
or the internal vQPU.
