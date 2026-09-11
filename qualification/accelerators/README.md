# Public accelerator qualification

This experiment distinguishes a useful simulation method from an old Marqov backend
name or a QB commercial plugin. It changes no hosted backend registry or availability.

## Current source mapping

Inspected Qristal Core `a5c3e5fa544c07d538974d3a289b19652d483848`; qualification
base `f90fda3adc625570851c9b350d9ba09c90394980`. Findings checked 2026-09-11:

| Historical target | Actual boundary | Public qualification path |
| --- | --- | --- |
| `cudaq:custatevec_fp64` | Qristal loads legacy CUDA-Q simulator libraries dynamically | Test current standalone CUDA-Q `nvidia`, `option=fp64`; then separately qualify Core integration |
| `cudaq:qb_mps`, `qb-mps` | Qristal documentation identifies these as commercial Emulator GPU plugins | Public CUDA-Q `tensornet` is an alternative capability, not the same implementation |
| `cudaq:dm` | Documented as a CPU density-matrix simulator | Do not count this label as GPU evidence; Aer `density_matrix` provides a separate CPU path |
| `tnqvm` | Public CPU MPS method; Core pins QB GitLab forks | Aer `matrix_product_state` is an available public CPU alternative; TNQVM reconstruction remains separate |

Sources: [Qristal backends](https://qristal.readthedocs.io/en/stable/rst/backends.html),
[NVIDIA simulator targets](https://nvidia.github.io/cuda-quantum/latest/using/backends/simulators.html),
[CUDA-Q 0.15.0 release](https://github.com/NVIDIA/cuda-quantum/releases/tag/0.15.0).
These are source/documentation findings, not evidence of deployed Marqov behavior.

Core `cmake/dependencies.cmake:361` and `:376` pin ExaTN `1a2e8944` and TNQVM
`8d8463ad` on QB GitLab. The public [ExaTN](https://github.com/ORNL-QCI/exatn)
and [TNQVM](https://github.com/ORNL-QCI/tnqvm) repositories are accessible, but
GitHub returned “No commit found” for those respective revisions. We have not
established their equivalence to a public revision or compiled a replacement.
Core detects `nvq++` without an explicit CUDA-Q version constraint, expects a list
of older named libraries in `cmake/cpp_lib.cmake:174`, and discovers simulator
libraries in `src/cudaq/sim_pool.cpp:42`. A current upstream GPU run cannot certify
that this older C++ adapter links or behaves correctly with CUDA-Q 0.15.

## Fixed correctness matrix

`fixtures.py` defines asymmetric X-first/X-last bit-order probes, H/H interference,
Bell, eight-qubit GHZ and inverse-GHZ circuits. Every result must conserve 16,384
shots, use logical-qubit-zero-first strings and satisfy the declared distribution.
Endpoints require exact counts; probabilistic outcomes use absolute tolerance .025.
These are small correctness cases, not qubit-capacity or speed claims. The same
vectors are checked against independent analytic expectations for every runtime.

### CPU method baseline

```sh
python3 qualification/accelerators/qualify_cpu.py --output /tmp/qristal-cpu-methods-new
PYTHONPATH=qualification/accelerators python3 -m unittest test_fixtures test_evidence
```

The first command requires the previously qualified local CPU image and launches
one restricted container, without a build, pull, host mounts or network. It runs
all six cases with QPP and explicit Aer `matrix_product_state` and `density_matrix`
settings. Source/input definitions, counts and cleanup evidence are retained.

The inspected XACC plugin explicitly writes the requested method into the Aer QObj
(`quantum/plugins/ibm/aer/accelerator/aer_accelerator.cpp:260`). It does not select
`automatic` for these two settings. The result interface does not export Aer’s
internal execution-method metadata; this evidence combines explicit configuration,
source inspection and observed counts. It is not a profiler trace. This does not
qualify noise on those methods, large MPS bond dimensions or truncation accuracy.

### GPU probe

Official NVIDIA CUDA-Q `cu12-0.15.0` Linux amd64 image manifest:

`nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a`

The image index was inspected without a local image download. CUDA-Q's open-source
code uses NVIDIA GPU runtime libraries; this is not a claim that all packaged
libraries have Apache-2 licensing.

On an already authorized disposable NVIDIA host with Docker/NVIDIA container
support, place `fixtures.py`, `gpu_probe.py`, `run_gpu.py` and the existing
`qualification/runtime/bounded_process.py` together in a read-only probe directory.
After pulling the pinned image on that host:

```sh
python3 run_gpu.py --output /var/tmp/qb-gpu-output-new
```

`gpu_probe.py` requires an available GPU, explicitly selects `nvidia` with fp64 or
`tensornet`, rejects target mismatches, applies the exact fixture gates and checks
loaded cuStateVec/cuTensorNet library paths. It never retries through a CPU target.
Target selection plus loaded libraries and correctness results are evidence of
GPU-path execution, not a kernel profiler trace or performance measurement.

The host runner uses two fresh non-root containers, no network, a read-only root
and probe mount, 512 MiB executable tmpfs, four CPUs, 12 GiB memory, 512 PIDs and no
capabilities. Each target has a 300-second deadline and bounded stdout/stderr.
Owned containers are removed even after failure. An independent host lifetime
limit is still required; this script does not provision or terminate its host.

## Bounded AWS execution scope

One `g5.xlarge` (A10G), us-east-1, official AWS Ubuntu 22.04 GPU base AMI
`ami-0eb7d782cce2fe526` (20260907). AWS read-only preflight found quota for eight
G/VT vCPUs and no running G/VT instances. RunInstances dry-run succeeded. The AWS
Pricing API reported Linux On-Demand compute at $1.006/hour, excluding storage/IP.
The run uses a 200 GiB encrypted gp3 root with delete-on-termination, no IAM role,
no SSH key, no inbound rules and HTTPS-only public egress to fetch the image.

The observer terminates the instance at one hour or completion; the guest also
schedules shutdown after 55 minutes and terminates on script exit. Instance-initiated
shutdown behavior is terminate. Result JSON is retrieved through EC2 console output;
no application credentials, S3 bucket or hosted Marqov job are involved. Instance,
volume and security-group deletion must be verified before calling the run finished.
A passed GPU probe would qualify upstream feasibility only; distribution, Qristal
Core adaptation, hosted isolation/lifecycle and noisy GPU behavior remain separate.

## Bounded follow-up work

Reuse platform issue [#691](https://github.com/marqov-dev/marqov-platform/issues/691)
as the historical GPU tracking context, correcting the backend mapping before
planning implementation. Its old worker paths and availability claims are not
acceptance criteria for a new executor.

1. After standalone GPU correctness passes, qualify one explicit runtime adapter:
   either an upstream CUDA-Q process adapter, or a separately built Core/CUDA-Q
   bridge if preserving Core API semantics is necessary. Bind the image digest,
   target, circuit/options schema, bit order and result schema; reject unsupported
   targets. A direct upstream adapter need not resurrect the old QB worker image.
2. Separately exercise cancellation, timeout, output limits and cleanup with GPU
   contexts, then agree an isolation/admission contract with the managed-execution
   owner. These fixed local container tests are not tenant-isolation certification.
3. Treat public TNQVM/ExaTN reconstruction as an independent compatibility spike:
   choose public revisions explicitly, build without QB GitLab, and compare exact
   small circuits before considering truncation/performance tests. Aer MPS already
   offers useful CPU tensor-network capability without claiming TNQVM equivalence.

Keep all three off the SDK/compiler release critical path unless an explicit
product requirement creates a dependency. The commercial Emulator and internal
vQPU remain outside this public-runtime qualification. No platform issue is closed
and no backend is enabled by these results.

## Recorded outcome

[CPU evidence](../evidence/2026-09-11-cpu-methods/README.md): 18 native cases passed
across QPP, Aer MPS and Aer density matrix.
[GPU evidence](../evidence/2026-09-11-gpu-feasibility/README.md): 12 native cases
passed across standalone CUDA-Q state-vector and tensor-network targets on A10G.
Fifteen offline regression/evidence tests pass. Earlier failed attempts and console
transport normalization are recorded alongside the successful GPU observations.
