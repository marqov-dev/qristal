# GPU workload adapter and local lifecycle — 11 September 2026

**Passed on NVIDIA A10G: twelve native adapter cases, three GPU-context fault
cases, and one fresh post-fault recovery case.** Six circuits ran through the
bounded typed-artifact CLI on each of `nvidia` fp64 and `tensornet`, at 16,384 shots.
Input hashes, candidate counts, bit ordering and exact adapter/runtime provenance
are retained in `result.json`.

The fault fixtures first sampled a circuit, then held their GPU context. The host
confirmed that an NVIDIA compute PID belonged to the exact owned container before
testing requested kill, timeout and output overflow. Each observed exit 137 and
non-running state, then independently removed the container and observed no GPU
compute processes. A fresh nvidia X-first case subsequently returned `100: 16384`.
The fault tests do not demonstrate interruption of a long-running CUDA kernel or
GPU memory sanitization between tenants.

| Observation | Outcome |
| --- | --- |
| Typed-artifact circuit matrix | 12/12 cases passed; exact candidate input and source binding |
| Requested kill | Owned GPU context observed; killed; exit 137; local stopped state |
| Three-second observation timeout | Timeout detected; explicit subsequent kill; exit 137; local stopped state |
| Four-KiB stdout overflow | Output bound detected; explicit subsequent kill; exit 137; local stopped state |
| GPU process removal | Observed after every owned-container removal |
| Fresh recovery | X-first returned `100: 16384` after all three faults |
| Hardware/runtime | A10G; driver 595.91.07; CUDA-Q 0.15.0; pinned official image |

Candidate data is not an accepted platform result. Local process/container state
is not a hosted provider STOPPED receipt or authorization to release capacity or
settle billing. No shared platform/SDK integration or release infrastructure was
changed. Qristal Core/CUDA-Q compatibility and hosted isolation remain unqualified.

`console-chunks.txt` preserves the short checksummed result chunks from EC2 without
unrelated boot output, cloud identifiers or private addresses. Chunk reassembly
checks duplicate agreement, bounds, decompression completion and SHA-256 before
reading the JSON. `result.json` is that decoded payload, pretty-printed without
changing its values. The source hashes bind the exact files staged on the GPU host.

Recheck the saved observations without AWS, Docker or CUDA-Q:

```sh
python3 qualification/gpu_adapter/check_evidence.py \
  qualification/evidence/2026-09-11-gpu-adapter
PYTHONPATH=qualification/gpu_adapter python3 -m unittest \
  test_adapter test_console test_evidence
```

Sixteen local regression/evidence tests pass; synthetic mocks are not counted as
native executions. See [the adapter procedure and proposed platform mapping](../../gpu_adapter/README.md)
for boundaries, reproduction, supported gates and required external authorities.

The temporary AWS instance, encrypted root volume and dedicated security group
were deleted and verified. `cleanup.json` records those checks; `manifest.json`
records the bounded host configuration and evidence hashes. This run required no
retry. It deployed no persistent service or platform infrastructure.
