# Public GPU feasibility — 11 September 2026

**Passed: twelve native correctness cases on one NVIDIA A10G**, six each on
CUDA-Q `nvidia` with fp64 and `tensornet`. This is standalone NVIDIA CUDA-Q
execution, not a rebuilt Qristal Core/CUDA-Q bridge, QB commercial Emulator,
QB hardware measurement, or hosted Marqov job.

| Property | Observed value |
| --- | --- |
| Runtime | CUDA-Q amd64-cu12-0.15.0, upstream revision `f6d1f1d50d9cd4fef60011197cafe67c9035c3dc` |
| Hardware | NVIDIA A10G, driver 595.91.07, 23028 MiB reported GPU memory |
| Cases per target | X-first, X-last, H/H interference, Bell, GHZ8, inverse-GHZ4 |
| Sampling | 16,384 shots per case; seed 42; deterministic endpoints exact; probabilistic tolerance .025 |
| State-vector Bell counts | `00: 8148`, `11: 8236` |
| Tensor-network Bell counts | `00: 8228`, `11: 8156` |
| GPU path evidence | Explicit targets, one visible GPU, `libnvqir-cusvsim-fp64.so` / `libnvqir-tensornet.so`, cuStateVec/cuTensorNet libraries |
| Workload boundary | Two fresh non-root, network-disabled containers; 4 CPU / 12 GiB RAM; 300-second target deadlines |

`result.json` retains all counts, expected distributions, canonical program hashes,
image digest and exact deployed probe-source hashes. No target falls back to CPU.
Loaded libraries and explicit target selection support GPU-path execution; this
is not a kernel profiler trace, throughput benchmark, scalability test, tensor
truncation study, noisy-GPU qualification or multi-tenant security certification.

## Evidence transport and earlier failures

EC2 inserted ISO timestamp annotations within long console lines, including inside
hash strings. `console-payloads.txt` retains the two original JSON payload copies
without unrelated console output. Only the transport annotations were removed;
the two normalized copies are identical, and program and source hashes then verify.
No counts or simulator output were repaired. Reproduce normalization with:

```sh
python3 qualification/accelerators/normalize_console.py \
  qualification/evidence/2026-09-11-gpu-feasibility/console-payloads.txt
python3 qualification/accelerators/check_evidence.py \
  qualification/evidence/2026-09-11-gpu-feasibility/result.json
PYTHONPATH=qualification/accelerators python3 -m unittest test_fixtures test_evidence
```

`attempts.json` records an observer decoding failure, a capacity-rejected launch,
and a Python SampleResult conversion failure before the successful corrected run.
The conversion regression is covered by a synthetic SampleResult test that yields
keys on iteration. Synthetic tests are not included in the twelve native cases.
The successful experiment used the documented `.items()` API:
[NVIDIA SampleResult reference](https://nvidia.github.io/cuda-quantum/latest/api/languages/python_api.html#cudaq.SampleResult.items).

AWS resource identifiers, private addresses and unrelated boot output are omitted
from this public record. All three launched instances, their root volumes and all four temporary security groups were deleted and verified. Cloud cleanup assertions are retained separately. See the
[procedure and follow-up scope](../../accelerators/README.md) for instance/image
pins, bounded provisioning, Core compatibility gaps and historical target mapping.
