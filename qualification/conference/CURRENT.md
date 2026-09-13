# Quantum Brilliance × Marqov: what we can demonstrate

Updated 13 September 2026. Evidence baseline: Qristal main
`43755ba213aa04c4cd40b8479040b034c740a80e` (PR31 merged).
This is an experimental public-software maintenance project. No QB partnership
or endorsement is claimed.

**The proposition:** preserve useful public Qristal capabilities, make experiments
reproducible, and provide a route toward isolated CPU, GPU and QPU workflows in
Marqov. We have working saved CPU/GPU demonstrations; hosted execution and a
supported public distribution remain separate gates.

## Lead with these three demonstrations

| Demonstration | What the evidence establishes | What it does not establish |
|---|---|---|
| One circuit family, five simulation methods | Six analytic cases each on QPP, Aer MPS, Aer density matrix, CUDA-Q nvidia fp64 and CUDA-Q tensornet; GPU runs used A10G | Speed advantage, maximum capacity, the older Core GPU bridge, or QB hardware performance |
| Readout noise and fresh calibration | 50 sweep cases, 26 calibration/mitigation executions and 40 drift cases; fresh calibration improves estimates in the tested model | Full SPAM, correlated/device noise, or universal accuracy improvement |
| Packaging and recovery | Exact private GPU candidate tested natively; bounded fault/recovery evidence with original failures and cleanup records | Public distribution, long-running CUDA-kernel interruption, multi-tenant security or admitted hosted Marqov jobs |

Evidence: [CPU/GPU methods](../accelerators/README.md),
[GPU published candidate](../evidence/2026-09-11-gpu-published/README.md),
[mitigation](../evidence/2026-09-12-readout-mitigation/README.md),
[drift](../evidence/2026-09-12-readout-drift/README.md).

**A useful scientific story:** stale calibration can make estimates worse even
when the underlying readout noise improves. In the restricted native drift
experiment, one stale correction produced 4.45 times the raw error. The separate
10,000-repetition synthetic coverage study shows why narrow sampling intervals
can miss systematic mismatch. Keep native and synthetic evidence separate.

## What the public maintenance work has recovered

The public CPU reconstruction has installed Core, selected Integrations and
simplified Decoder evidence. Core's Qiskit0.46 and Integrations' Qiskit1.2
requirements use separate environments. Standalone upstream CUDA-Q supplies the
demonstrated GPU alternative. These runtimes can sit behind an isolated execution
adapter; they do not require relaxing the platform SDK's Python requirement or
restoring historical polling workers.

The public QFT/IQFT provider also passed 70 phase-sensitive small QPP checks.
That is optional technical appendix material, alongside source and artifact
provenance. It is not a claim that every Qristal feature has been recovered.

## Decoder is a separate research track

The Decoder is an application for sequence/beam decoding, originally aimed at
speech-to-text. Simplified fixtures work. Full Decoder remains incomplete: the
latest O1/O3 paired experiments all timed out at the unchanged60-second bound.
A qualified diagnostic representation removed the earlier controlled-Z synthesis
stall; preparation/simulation cost now dominates. No quantum advantage or correct
full decoded answer has been demonstrated.

Two independent Claude Code lanes now investigate scientific papers and targeted
engineering. Their reports and patches require review; delegation is not new
experimental evidence. This work does not block the platform or existing demos.
See [current native findings](../evidence/2026-09-13-sparse-state-o3/README.md) and
[tracking issue #2173](https://github.com/marqov-dev/marqov-platform/issues/2173).

## The conference conversation

1. Show the noise/calibration story and the CPU/GPU correlation comparison.
2. Explain the maintenance boundary: public software, reproducible evidence,
   careful packaging, and explicit unqualified capabilities.
3. Ask which public examples and user workflows QB would find most useful, and
   whether they would collaborate on validation and maintenance.
4. Explore future hardware comparisons and commercial Emulator access as
   partnership possibilities. Neither commercial Emulator nor internal vQPU was
   reconstructed or is needed for the demonstrations above.

Use the [five-minute walkthrough](WALKTHROUGH.md) and
[Marqov report](https://app.marqov.ai/projects/776ca156-9051-4fcb-8aca-202e78a94cac/report).
The report contains saved experiments, not completed hosted jobs. The
[offline packet](packet/README.md) embeds five charts and retains selected evidence.
A human opening/rehearsal of the exported HTML remains required: automated local
browser inspection was blocked by file-URL policy and was not worked around.

## Next outside Decoder, in priority order

- Complete the human conference walkthrough and keep the verified downloadable
  backup available (#2172).
- Finish candidate distribution/acquisition/notice and exact CPU-artifact gates
  (#609/#640), keeping source forks distinct from licensing of the assembled runtime.
- Qualify or explicitly leave unsupported the older Core GPU bridge and TNQVM
  (#691/#1701). Standalone CUDA-Q evidence cannot substitute for these paths.
- Integrate through the platform owner's current admission/result/lifecycle
  contracts when that lane is ready (#338/#704). Do not revive historical routes.

The [maintenance matrix](../MAINTENANCE.md) defines detailed boundaries.
