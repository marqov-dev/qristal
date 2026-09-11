# Explicit CPU simulation methods — 2026-09-11

**Passed: 18 native executions**, six analytic circuits each on QPP, Aer
`matrix_product_state`, and Aer `density_matrix`. Each used 16,384 shots.
The restricted container was removed and its absence verified.

`cpu.stdout` contains actual counts, requested methods and program hashes;
`cpu.stderr` is empty. `intent.json` records the run boundary, `cleanup.json`
records container cleanup, and `manifest.json` hashes both evidence and the exact
probe sources. Recheck counts with the accelerator fixture tests.

This extends the CPU correctness baseline to explicit MPS and density-matrix
settings. It does not establish TNQVM reconstruction, GPU execution, noisy MPS,
large-circuit accuracy, performance, or hosted Marqov availability. Aer method
selection is supported by explicit settings and inspected XACC source; the result
API does not return an internal Aer method trace.

See [the qualification procedure](../../accelerators/README.md) for source pins,
commands, fixed circuits, limits and the separate GPU/Core boundary.
