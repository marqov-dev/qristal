# Phase composition and actual Decoder preparation inventory

PR29 merged at `4182e377fb2a1d795807b934af711ba2d12d7f7b`. This independently owned CPU experiment ran qualification source `19a853df44f7f84de87176c3a6a248997ea2f239`, under the committed [protocol](../../full_decoder/cloud/PHASE-COMPOSITION-PROTOCOL.md). It did not change production Core, Decoder, runtime locks, shared platform/SDK checkouts or hosted admission.

## What changed our understanding

**The additional-control test did not show a probability error.** Four candidate cases and four selected legacy compiled-IR observations used Rx angles ±0.37 and ±0.9, each exact lowered circuit twice. Candidate outer-one probabilities were at most 1.252e-32; legacy at most 5.817e-32. Legacy vectors retain an overall phase of approximately −π/8 relative to the candidate. No phase fitting is used to pass an exact-state gate, and these diagnostic legacy observations do not qualify generic controlled composition. The earlier standalone exact-phase mismatch remains recorded; this experiment does not demonstrate a wrong Decoder answer or justify an urgent upstream phase repair.

**Narrow inverse preservation cannot be assumed to solve the timeout.** Construction-only inventory of the unchanged 24-qubit fixture found:

| Structure | Raw nodes, including composites | Primitive leaves | Eligible single-gate controlled blocks | Estimated sparse visits |
|---|---:|---:|---:|---:|
| Entire preparation | 95,425 | 95,271 | 41 | 93,426 |
| DecoderKernel child | 95,410 | 95,262 | 39 | 93,413 |
| Legacy inverse | 95,272 | 95,271 | 0 | 95,272 |

The other top-level children contain only 14 nodes combined. The root accounts for the remaining node. The estimator excludes descendants of supported controlled X/Y/Z/H/Rx/Ry/Rz blocks; it predicts structure, not elapsed time, active amplitudes or independent gate cost. Its forward count agrees with the prior traversal profile to the profiler's root convention. The entire raw-to-direct difference is only 1,999 nodes (2.095%); actual forward traversal already uses these shortcuts. Inverse traversal is only about 1.98% above forward, despite the prior roughly twofold time difference.

The actual structure includes eight amplitude-estimation blocks, eight phase-estimation blocks, two MeanValueFinder blocks and fourteen nested inverse blocks. This confirms presence, not exclusive runtime attribution or a count of distinct logical algorithms. Flattened inverse construction loses all controlled metadata.

## Evidence and limits

`result.json` is bound to checksummed `console-filtered.json`. `complex-states.json`, `preparation-inventory.json` and `analysis.json` are independently replayed by `analyze_composition.py`. All compile/provider/composition stages exited zero. The inventory consumer deliberately exited **1** with `QB_INVENTORY_ONLY_STOP` after its completion marker, before search or simulation. This is expected diagnostic termination, **not** a completed Decoder caller result.

The protocol used one m7i.large, 4 GiB process address-space limit, non-root network-isolated consumers, 180-second compile limits and 60-second consumer limits. Loaded runtime-library hashes, executable identities, original/derived Decoder source hashes and archive identity are retained. Source checkout revisions do not imply cached installed dependencies were rebuilt. The diagnostic QFT provider was rebuilt for this run; its prior 70-vector qualification was not repeated here.

The instance, exact disks/security group and transfer resources were all removed automatically. Public infrastructure identifiers use consistent opaque aliases; original durable audit files remain local. No credentials, signed URLs or raw bootstrap content are published.

## Next work, in priority order

1. Measure inside the actual DecoderKernel preparation: retain hierarchical circuit paths and controlled-base vocabulary, and observe sparse-state cardinality and deferred-operation queue sizes without calling a state dump or flushing queues. Keep timing/count claims separate; instrumentation overhead needs a matched baseline.
2. Choose a change from those measurements, protecting independent complex-state and caller-oracle correctness. Do not expand the narrow inverse prototype across all preparation merely because it passes its small gate set.
3. Run the original full Decoder fixture through caller completion, then characterize stochastic success. Installed-plugin and exact distribution-image qualification remain separate promotion gates.
4. Keep the selected legacy phase discrepancy as a bounded compatibility investigation. This run lowers its priority relative to the measured preparation cost; it neither erases the exact-phase mismatch nor proves all compositions safe.

Track remaining work in [platform #2173](https://github.com/marqov-dev/marqov-platform/issues/2173), under [#1701](https://github.com/marqov-dev/marqov-platform/issues/1701). Prior public CPU/GPU/readout conference evidence remains valid within its documented scope; full Decoder and hosted availability remain unqualified.
