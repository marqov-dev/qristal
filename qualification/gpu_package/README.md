# Packaged standalone GPU runtime qualification

This package adds the already qualified workload adapter to NVIDIA's existing CUDA-Q container. It does not rebuild CUDA-Q, install Python packages, modify Core, or restore the historical QB worker. It is independent of the platform/SDK release path.

## Research reused

Reviewed 11 September 2026:

- [NVIDIA local installation](https://nvidia.github.io/cuda-quantum/latest/using/install/local_installation.html): the container includes the runtime libraries, while GPU use requires suitable hardware/drivers and GPU exposure. Use that supported distribution instead of rebuilding its dependency graph.
- [Docker build practices](https://docs.docker.com/build/building/best-practices/): pin the base digest and control the build context. Our context contains exactly three Python files, payload hashes and the Dockerfile; no repository checkout, credentials or dependency resolution enters the image.
- [NVIDIA device visibility controls](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html): the no-GPU negative case uses `NVIDIA_VISIBLE_DEVICES=void` and no `--gpus` flag. Qualified GPU cases explicitly request the device.

The existing CPU runtime, native fixture matrix, bounded-process helper and fault harness are reused. `qualify.py` replaces only the native harness's container-creation function: baked `/opt/marqov-qb` code, an immutable Docker image ID, and one read-only `/inputs` mount. Tests verify the actual image/mount observations; no source-code overlay enters the workload.

## Build and test

On an authorized disposable Linux amd64 GPU host with Docker/NVIDIA support, pull the exact base from `Dockerfile`, then from this checkout:

```sh
python3 qualification/gpu_package/build.py --output /var/tmp/qb-build-new
python3 qualification/gpu_package/qualify.py --build /var/tmp/qb-build-new/build.json --output /var/tmp/qb-qualification-new
```

Both output directories must be new. Do not run this on a shared GPU host: the inherited fixture requires no other GPU processes. The hardware experiment requires separate capacity authorization. Local regression tests need no GPU:

```sh
python3 -m unittest discover -s qualification/gpu_package -p 'test_*.py'
```

The build uses the pinned Linux amd64 CUDA-Q 0.15.0 CUDA-12 image and no dependency installation. The native driver and NVIDIA container toolkit belong to the host, not the image. The build explicitly sets directory traversal permissions and checks file readability as the runtime user. The resulting image defaults to non-root, `/tmp` as home/workdir and the bounded adapter entrypoint. The fixed fault helper is included for qualification, but is not a user-selectable adapter operation. The container can be explicitly overridden by the operator; its CLI is not an isolation boundary.

## Identity and evidence semantics

`build.json` records the Docker image ID, base registry manifest digest, Dockerfile hash and payload-file hashes. A local Docker content-addressed image identity is not evidence of a published registry artifact (its representation also depends on the Docker image store). A future registry release must record its own manifest digest and qualify that identity; this work does not publish an image or establish bit-for-bit reproducible rebuilds.

The unchanged workload candidate's `runtime_image` field identifies its expected upstream base. It must **not** be relabelled as the derivative identity. The outer report separately records the built image ID and the inspected image ID for every container, plus hashes read from the baked files. These are operator observations, not authenticated platform receipts. The old base-image candidate mapping does not thereby admit this derivative as a hosted runtime.

The matrix runs six circuits on each of `nvidia` fp64 and `tensornet`, invalid input and no-GPU negatives, requested stop/timeout/overflow while holding an observed GPU context, and a fresh recovery case. Counts and shot totals use the existing independent analytic checks. No long-kernel cancellation, memory sanitization, maximum scale or performance claim is implied.

## Inventory and distribution

`inventory.py` collects Python version/packages, dpkg package versions, baked-file hashes and discovered license/notice file hashes under selected NVIDIA/runtime directories. It reads no environment or host secrets. This is a dependency inventory, not a complete SPDX/CycloneDX SBOM, vulnerability audit or legal clearance. Discovery is deliberately scoped and does not prove every license was found.

CUDA-Q source licensing, NVIDIA runtime library licensing, base OS packages and Marqov/Qristal source licensing are separate. Do not label the entire derived image Apache-2.0. Retain upstream notices and review redistribution terms for the exact bundled components before publishing a registry artifact. The source recipe and private qualification do not themselves establish distribution permission.

The bounded AWS experiment reuses the prior role-free, no-inbound, one-instance harness, with a 55-minute shutdown fallback, external one-hour observation/termination bound and exact instance/disk/security-group cleanup. No IAM role, SSH key or hosted service is introduced. Host source is staged only to build/run the supervisor; workload containers see only packaged code and input JSON.

Primary license references: [CUDA-Q source license](https://github.com/NVIDIA/cuda-quantum/blob/main/LICENSE), [cuQuantum software agreement](https://docs.nvidia.com/cuda/cuquantum/latest/license.html). These moving upstream documents guide the distribution review; the experiment's package/version inventory is the record of what was actually installed. The runtime keeps the base filesystem and notices intact rather than copying selected NVIDIA binaries into an unrelated base.

The [upstream release Dockerfile at the tested CUDA-Q revision](https://github.com/NVIDIA/cuda-quantum/blob/f6d1f1d50d9cd4fef60011197cafe67c9035c3dc/docker/release/cudaq.Dockerfile) also documents hard-coded dependency locations and an asset migration step. Keeping those paths intact is another reason to derive from the released image instead of relocating a subset of libraries.

## Recorded native result

[11 September 2026 evidence](../evidence/2026-09-11-gpu-package/README.md) records
a passing build, twelve circuits, two negatives, three context faults and fresh
recovery on A10G. It includes the unsuccessful attempts and exact source hashes.
The successful console payload was recovered from complete duplicate records
with original checksum and prefix verification; the strict original decoder was
not weakened. Run `check_evidence.py` for the package-specific offline checks.
