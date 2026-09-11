# Offline GPU mapping replay — 11 September 2026

Passed: twelve retained native candidates through the same offline mapper under
two synthetic engine labels, with identical previews and independent analytic
count checks. Twelve regression tests pass. **No new GPU execution took place.**

Source baseline: Qristal `6de01a6158779e837a965d444d95015d075dd322`, merged PR #12.
The input observations come from the existing 2026-09-11 GPU-adapter evidence.
`replay.json` records each preview and parity observation; `manifest.json` binds
that output, the source files and native input evidence.

Candidates are reconstructed from the retained parsed candidate objects using
explicit sorted-key compact JSON. A preview's candidate SHA-256 binds those replay
bytes, not an unavailable original raw CLI stdout stream. Original input artifacts
are independently reconstructed using the fixed circuits and the native harness's
serialization and checked against native candidate input hashes. No native counts,
source bindings or program expectations are changed.

These are review fixtures, not authenticated admitted context or accepted hosted
results. Engine labels do not run Direct or Temporal. The context and output are
local Python objects, not a proposed new hosted protocol. See [procedure and limits](../../gpu_mapping/README.md).
