# Public-source CPU qualification

This directory is original community maintenance material. It does not establish a supported Qristal release. See STATUS.md for the boundaries of the evidence.

## Prepare

Use a dedicated parent directory with this repository checked out as `qristal`. Scripts place sources and build outputs alongside it. They never access a Marqov platform or SDK checkout.

```
python3 qristal/qualification/prepare_sources.py
python3 qristal/qualification/build_toolchain.py
python3 qristal/qualification/run_stage.py configure
python3 qristal/qualification/run_stage.py build
python3 qristal/qualification/run_stage.py test
python3 qristal/qualification/run_stage.py linkage
python3 qristal/qualification/run_stage.py install
```

Preparation fetches public sources using anonymous Git, checks the selected revisions and Boost checksum, and applies the included XACC compatibility patches. The toolchain comes from a digest-selected public Ubuntu 22.04 base. Ubuntu package versions are recorded in `toolchain-packages.txt`; apt repositories are not snapshot-pinned yet, so this is not a byte-reproducible toolchain recipe.

Build and tests run without networking, in a read-only container with two CPUs, 4 GiB memory including swap, and a 256-process cap. Only the dedicated work directory and temporary storage are writable. The toolchain acquisition step uses networking to install Ubuntu packages in its disposable container. No host dependencies are installed. No QB binary image, SDK installation or commercial plugin is an input.

The CPU profile selects qpp plus public circuit optimizers and the Staq OpenQASM compiler, its XASM dependency, and the public IBM/Aer stack that supplies the Qobj compiler and native CPU Aer backend. It is not an all-plugin XACC build. The ACZ patch supplies anti-controlled Z using X(control), CZ, X(control). Tests check gate registration, phase-sensitive interference in both control orders and states, and Bell correlations. A nonzero process exit, runtime error log, or missing PASS marker fails the test.

## Core investigation

The source-preparation script checks out the pinned merged `qristal-core` revision. The older `core-compatibility.patch` is retained as historical evidence and is no longer applied. Eight ideal CPU fixtures now pass against the rebuilt Python extension, including OpenQASM input, optimization, transpilation and result retrieval. This is a build-tree qualification, not a clean installed-distribution test.

```
python3 qristal/qualification/run_stage.py core-configure
python3 qristal/qualification/run_stage.py core-build
python3 qristal/qualification/run_stage.py core-plugins
python3 qristal/qualification/run_stage.py core-test
```

The test launcher exposes the rebuilt Python extension through a temporary namespace package and links the two rebuilt Core transpiler plugins into the isolated XACC prefix. An explicitly empty backend database is used. No existing backend configuration is read. Configuration may fetch public C++ and Python dependencies; subsequent compilation is offline. ExaTN/TNQVM are explicitly disabled for this first profile, and no CUDA compiler is installed.

Every stage writes a log and a JSON metadata record beside the checkout. Do not describe a component as qualified until its runtime tests and applicable correctness tests have passed. The compiler flags use modest optimization for local qualification; these results are not performance benchmarks.

## CPU noise qualification

After the Core stages, run `python3 qristal/qualification/run_stage.py noise-test`. This exercises native CPU Aer with analytically specified readout, amplitude-damping and symmetric Pauli-noise probabilities. It does not exercise pulse simulation, cloud IBM services, GPU acceleration, commercial Emulator models or a QB device model. The environment is empty of provider credentials and runtime networking is disabled.

`python-constraints.txt` records the resolved Python package versions from the first CPU qualification. Core dependency acquisition uses these constraints. C++ sources and the public toolchain remain pinned/recorded separately.

## Installed runtime

The next qualification stage verifies CPU execution with source and build trees unmounted, including an independent installed Core C++ consumer. See [installed runtime reproduction and limits](installed/README.md). Its source lock includes the Core Eigen packaging fix under review in Core PR #2.

## Local CPU image

The installed runtime is now packaged and exercised without host mounts. See the [local image recipe, evidence and adapter proposal](runtime/README.md). No registry publication or platform connection is implied.

## Additional CPU methods and public GPU feasibility

See [accelerator qualification](accelerators/README.md) for explicit Aer MPS and
density-matrix results, the corrected historical backend mapping, and a bounded
standalone CUDA-Q GPU probe. GPU feasibility is separate from Core integration.
