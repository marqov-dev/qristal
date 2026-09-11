# Standalone CUDA-Q workload adapter qualification

This is an isolated workload CLI and a disposable-host test harness. It is not a
platform admission/control envelope, accepted-plan/result receipt, provider
adapter, or authority writer. No shared platform or SDK code is changed.

## Input and output

`adapter.py` reads one regular, non-symlink UTF-8 JSON file of at most 16 KiB and
checks its exact SHA-256 before importing CUDA-Q. The provisional data artifact is:

```json
{"schema":"qristal.cudaq-circuit/v1","target":"nvidia","qubits":3,"shots":17,"seed":42,"gates":[["x",0]]}
```

It permits `nvidia` (fp64) and `tensornet`, 1–12 qubits, 1–16,384 shots, a bounded
integer seed and 1–256 X/H/CX gates. Measurement of all qubits is implicit at the
end. Duplicate/unknown keys, unsupported gates/parameters, same-control/target CX,
floating-point or boolean integers, invalid qubits and changed bytes fail closed.
It does not execute tenant Python or accept arbitrary source entrypoints. These
ceilings constrain qualification; they grant no hosted capacity or spend authority.

The candidate JSON includes exact input and adapter hashes, adapter version,
expected immutable image, explicit simulator and CUDA-Q version, loaded simulator
and GPU libraries, logical-qubit-zero-first counts, qubits, shots and seed. Missing
GPU, target mismatch, missing/wrong counts or GPU library evidence fail. No CPU
fallback exists. The image string inside workload output is a claim: a trusted
runner must independently bind the actual admitted image and artifact identities.

Inside the selected isolated NVIDIA container:

```sh
python3 -B /probe/adapter.py /probe/inputs/circuit.json --sha256 EXACT_INPUT_SHA256
```

The CLI emits candidate data only. Exit zero is not an accepted result, STOPPED
receipt or resource-release authorization. Exceptions produce a fixed failure
message and nonzero exit without reflecting arbitrary input/runtime diagnostics.
The outer runner must bound runtime and output and independently validate results.

## Qualification boundary

`qualify.py` expects the same digest-pinned official CUDA-Q image as the accelerator
matrix, Docker with NVIDIA support, and a dedicated authorized GPU host. Stage
`adapter.py`, `fault_workload.py`, `qualify.py`, the unchanged accelerator
`fixtures.py` and runtime `bounded_process.py` together in a root-owned readable
probe directory. The harness creates its fixed `inputs` directory there and runs:

```sh
python3 -B qualify.py --output /var/tmp/qb-adapter-output-new
```

It executes six analytic circuits per target in fresh non-root containers with no
network, read-only root/probe, bounded executable tmpfs, 4 CPUs, 12 GiB memory,
512 PIDs, no capabilities and bounded Docker logs. Each normal run has a 120-second
deadline and 128 KiB stdout / 16 KiB stderr limits. It checks source artifact
binding, counts, successful process exit and local container stopped state before
removing the owned container and observing no GPU compute processes.

Three separate fixtures create a GPU context and hold it. The host verifies an
NVIDIA compute PID belongs to that exact container before exercising requested
kill, a 3-second observation timeout, or a 4 KiB output-overflow boundary. Timeout
or output failure alone does not count as termination: the harness explicitly
kills the recorded container, checks exit 137 and non-running state, removes it,
and separately checks that GPU processes disappear. A final fresh sampling run
checks recovery after all three faults. The fixture is separate from the public
adapter and is never selectable through its circuit artifact.

These observations concern Docker and NVIDIA on a dedicated disposable host.
They do not establish GPU memory erasure, tenant isolation, preemption latency,
concurrent scheduling, orphan recovery after host loss, production provider
STOPPED proof or authorized billing/capacity release. No fleet is deployed.

Short indexed console chunks are compressed and SHA-256 bound. `console.py`
reassembles them only when complete, rejects conflicting duplicates and verifies
the payload hash. This avoids relying on a single long EC2 console line. Only
known timestamp annotations are stripped; malformed or changed payloads fail.

## Platform mapping for owner review

Inspected platform `origin/main` at `551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5`,
ADR-0016 and the common execution specification. The shared working checkout was
on another revision and was left untouched. On 11 September the release owner
confirmed independent workload-only qualification with the boundaries below:

| Workload material or observation | Proposed platform responsibility, not implemented here |
| --- | --- |
| Circuit data and exact byte hash | Accepted typed input artifact; trusted material resolver checks task/plan/profile and current disclosure authority |
| Fixed adapter and image | Admitted allowlisted runtime profile, dependency/source binding and authenticated runtime identity |
| Candidate counts and provenance | Validate against the reviewed result/display schema; bind exact request/attempt and use the existing authorized acceptance writer |
| Process completion | Observation only; cannot advance successors or release capacity |
| Kill, stopped container and empty GPU process table | Local qualification evidence; a real provider adapter still needs exact durable identity, fencing, independent terminal proof and authorized resource release |

Direct and Temporal execution should share these authorities. No new engine,
provider identity or control envelope is introduced. Core/CUDA-Q compatibility,
TNQVM reconstruction, commercial Emulator equivalence and hosted availability
remain separate. This work creates no dependency on the current release path.

Local regression tests require only the Python standard library:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=qualification/gpu_adapter \
  python3 -m unittest test_adapter test_console test_evidence
```

Synthetic runtime tests are clearly separate from any retained native GPU evidence.

## Recorded result

The [native evidence](../evidence/2026-09-11-gpu-adapter/README.md) passes twelve
adapter circuits, three owned-GPU-context fault cases and fresh recovery. Sixteen
local regression/evidence tests pass. This adds standalone workload and local
lifecycle evidence; the platform mapping above remains a review proposal.
