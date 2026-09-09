# Local CPU adapter evidence — 2026-09-09

Baseline: qristal `5c05fc886a725df3c9b8c2a3671c5962c05ed0d4` (merged image PR #4).
Platform contract snapshot inspected: `6c8400a0cf0bd3861e0f583f51a8f2339ec4da1f`.
The release owner approved only the workload-local CPU adapter and conformance
fixtures. Hosted QB artifact/profile admission remains undefined; the Python task
material gate and trusted execution lifecycle were not changed.

`image.json` records the tested local image/config ID and its qualified parent.
It is not a registry manifest digest and nothing was published or deployed.
`initial-overlay.json` retains the first manual overlay; the reproducible script
subsequently produced the final image. Both overlays contain the same adapter
source. Final pure/native checks and regressions target the final image.

- `test_adapter.py.log`: four pure unittest groups, covering option bounds,
  invalid probabilities and types, input bytes/declarations/includes, original
  program hash, exact shot totals, bit widths/types, maximum result size, and
  regular-file/symlink/FIFO handling.
- `test_adapter_image.py.log`: 14 real CLI cases. Both qpp and Aer return `10`
  for X on qubit 0 and `01` for X on qubit 1; both pass 1/12 qubits,
  1/16384 shots and seed endpoints. Comments work. Invalid noise, oversized
  arguments, excessive shots and an invalid native gate produce bounded errors.
- `regression-tests.json`: all ten pre-existing image groups, including the
  previous 43 CPU fixtures for Core, noise, Integrations and simplified Decoder,
  ideal/noisy Bell CLI, capability/invalid-input checks and image isolation.

Tests ran on local Docker linux/amd64 under emulation, offline, without host
mounts, as UID 65532, with read-only root, 128 MiB temporary scratch, 2 CPUs,
4 GiB memory including swap, 256 PIDs, dropped capabilities and no-new-privileges.
No GPU, hardware QPU, commercial Emulator/vQPU, calibrated device model,
hosted cancellation, provider identity or platform end-to-end test is claimed.

The controller must still enforce deadlines and treat missing/malformed output
as failure, even if native code exits with status zero. Full-register measurement
was qualified; arbitrary classical-register remapping was not. This adapter's
precheck is not a complete OpenQASM grammar or a hosted trust boundary.

Follow-up remains under platform #338 and post-release epic #1701: define the
admitted QB program/result artifact schemas and profile, then separately connect
the trusted material gateway/lifecycle. Do not put that work on the compiler
release critical path merely because local CPU conformance now passes.
