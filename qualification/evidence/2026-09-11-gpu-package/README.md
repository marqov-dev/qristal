# Packaged GPU qualification — 11 September 2026

The derivative image passed the native matrix without host-mounted source code. Source baseline was merged Qristal main `2fee33418f434a1e62913e36363f233e028fdf78`; `source-hashes.json` binds all nine exact staged build/runtime/harness files in this change. The build recipe and replay tools are in [gpu_package](../../gpu_package).

- 12 analytic circuit cases: six each on CUDA-Q `nvidia` fp64 and `tensornet`, 16,384 shots each.
- Invalid input and no-GPU cases: nonzero exit, no candidate, stopped container.
- Requested kill, timeout and output overflow: GPU context observed before the fault, container/process removal verified afterwards.
- A fresh state-vector recovery run returned `100: 16384`.
- All 19 created containers were observed using the same built image identity, with one read-only `/inputs` bind mount. Application code came from the image.
- Inventory: Python 3.12.3, 117 Python package metadata entries, 254 dpkg entries and six discovered license/notice files. No metadata or scoped license-scan errors were reported. This is not a complete SBOM or redistribution clearance.

Built Docker content identity: `sha256:c699932cbd0583b02594322e6aa8a22d7117be75cdcd00af0a7f9553f2e45185`.
Base registry digest: `sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a`.
Hardware: one g5.xlarge in us-east-1c, NVIDIA A10G, driver 595.91.07, 23,028 MiB reported GPU memory. Host AMI: `ami-0eb7d782cce2fe526` (AWS Deep Learning Base OSS NVIDIA Ubuntu 22.04, 20260907). The record does not establish immutable host kernel/container-toolkit identities or production runtime attestation.

The image was built and used on the disposable host. It was not pushed to a registry or retained after host teardown. A later release needs a retained registry artifact and its own digest qualification. The unchanged candidate's `runtime_image` refers to the upstream base; the outer build/container observations separately record the derivative. Neither is a platform acceptance receipt.

## Failure history and recovery

[First attempt](attempts/first): image built; inventory failed before simulation, with insufficient diagnostics. [Second attempt](attempts/second): bounded diagnostics showed the runtime user could not open the baked inventory script. The corrected recipe sets directory traversal permissions after COPY and checks readability under UID 65532 during build. [Capacity attempt](attempts/capacity): AWS rejected us-east-1b; the same instance type was retried in us-east-1c. Cleanup evidence is retained for every attempt.

The successful run emitted two console copies. One nonfinal chunk in one copy was truncated to 141 characters; its other copy had all 160. The original strict decoder rejected this as a conflict. `console-observed.txt` retains the records as observed. Recovery accepts only complete records, requires each truncated fragment to match the complete prefix, rejects stream/complete-copy conflicts, requires every index, and verifies the original full-payload SHA-256. `console-chunks.txt` and `console-recovery.json` record this selection; payload data was not edited. Four regression tests cover recovery, missing complete copies and conflicting complete/partial records.

## Verify offline

```sh
python3 qualification/gpu_package/check_evidence.py qualification/evidence/2026-09-11-gpu-package
python3 -m unittest discover -s qualification/gpu_package -p 'test_*.py'
```

The package suite contains 11 tests; the existing adapter suite has 16 passing tests. Counts and lifecycle checks reuse the existing analytic verifier. These tests validate retained observations and bindings, not authentic hosted execution.

## Limits

These are small synthetic correctness and context-holding fault fixtures. They do not prove performance, maximum capacity, long-running-kernel interruption, GPU memory sanitization, the Qristal Core/CUDA-Q bridge, TNQVM reconstruction, commercial QB Emulator access or hosted availability. No backend is enabled and no issue is closed by this evidence.
