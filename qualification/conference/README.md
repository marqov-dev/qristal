# Quantum Brilliance simulation research record — updated 12 September 2026

This is the entry point for engineering reports, conference demonstrations and future technical articles. The project distinguishes maintained public Qristal CPU capabilities from standalone NVIDIA GPU alternatives and from QB's commercial products. No partnership, endorsement, hosted availability or maximum scale is established.

## Evidence and capability ledger

Current evidence audit baseline: Qristal main `deb37d4a6dcfd05131592021c73b8c948bf37609` (PR18 merged). Platform contract review used `551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5`; subsequent platform changes require renewed review. Evidence directories retain their own source identities; these are not claims about deployed behavior.

| Capability | Observed evidence | Practical limit / next gate |
|---|---|---|
| Public CPU build and installed consumers | [Installed qualification](../installed): 8 Core ideal, 10 noise, 16 separate Qiskit 1.2 integration and 9 simplified decoder fixtures | Not every API or full decoder; Core parser and Integrations use different Qiskit environments |
| Restricted readout workflow | [11 analytic cases](../evidence/2026-09-11-readout-pipeline), seeds 7/42, 16,384 shots; 27 runtime methods and 8 checker tests | Generic asymmetric readout, not calibrated QB hardware or SPAM mitigation |
| Readout parameter sweep | [50 native Bell cases](../evidence/2026-09-11-readout-sweep): 25 settings, two seeds, 16,384 shots; maximum outcome residual 0.493 percentage points | Forward readout model only; no mitigation or hardware calibration |
| Independently calibrated readout correction | [26 native calibration/held-out executions](../evidence/2026-09-12-readout-mitigation), distinct seeds; aggregate observable error reduced 95.64–96.03%; near-singular control rejected | Ideal preparation, stationary q0-only readout model; signed estimates and calibration-inclusive uncertainty; not full SPAM/device calibration |
| CPU methods | [18 native cases](../evidence/2026-09-11-cpu-methods): QPP, Aer MPS, Aer density matrix | Explicit requested methods; no internal Aer profiler evidence; MPS is not reconstructed TNQVM |
| Public GPU alternatives | [12 native cases](../evidence/2026-09-11-gpu-feasibility): standalone CUDA-Q nvidia fp64 and tensornet on A10G | Small correctness matrix, not performance/capacity or Core/CUDA-Q bridge qualification |
| GPU workload adapter | [12 circuits, 3 fault cases, fresh recovery](../evidence/2026-09-11-gpu-adapter) | GPU context held during faults; not long-kernel interruption or memory sanitization proof |
| Published GPU candidate | [Exact digest on A10G](../evidence/2026-09-11-gpu-published): 12 circuits, 2 negatives, 3 faults, recovery; original SPDX/SLSA records retained | Private candidate; no hosted acceptance. Observer lost its exact volume ID; cleanup used instance/group absence and a full-region launch-window volume scan |
| Native supervisor restart | [Same A10G guest recovered after SIGKILL](../evidence/2026-09-11-supervisor-recovery); exact instance/disk/group cleanup after terminal-metadata correction, with unchanged deadlines | Control-plane/GPU health experiment, not simulator rerun or first-attempt unattended success |
| GPU candidate mapping | [12 retained candidates](../evidence/2026-09-11-gpu-mapping), 12 regression tests | Offline synthetic engine labels; plausible incorrect counts can pass integrity validation |
| CPU VM isolation feasibility | [Five Firecracker guests](../microvm): prepare, validate, QPP, termination, overflow | Bounded probes, not complete production security or authenticated lifecycle receipts |
| Hosted Marqov executor | [Profile review](../gpu_adapter/HOSTED-PROFILE-REVIEW.md), platform local rehearsal PR2145 | No hosted GPU admission, provider identity, transport, accepted results or catalog enablement |
| QB commercial Emulator / internal vQPU | No implementation or runtime qualification in this effort | Future partnership discussion; not recreated by these public alternatives |

Native CPU image: `sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44`.
GPU upstream image: `nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a`.
GPU hardware: A10G, driver 595.91.07, reported 23,028 MiB. The initial GPU qualification used source overlays. The later [packaged runtime experiment](../evidence/2026-09-11-gpu-package) passed without source overlays; [the private published digest also passed native qualification](../evidence/2026-09-11-gpu-published), with an explicitly documented observer interruption and cleanup-audit limitation. The NVIDIA image contains separately licensed components; the Qristal Apache license does not cover the entire distribution.

## What we learned, including failures

- Public CPU components can be built and consumed without the missing QB binary runtime. This establishes a maintainable subset, not universal reconstruction. See [source lock](../source-lock.json), [dependency constraints](../python-constraints.txt) and [qualification guide](../README.md).
- Backend names are not hardware evidence. Public `cudaq:dm` and `cudaq:qpp` descriptions must not be treated as GPU proofs. The legacy `qb_mps` commercial target is not interchangeable with public CUDA-Q tensornet. Historical 28/100-qubit and speed claims are not measured outcomes here.
- CPU Aer MPS and current standalone CUDA-Q offer useful alternative capabilities. The older Core bridge and unavailable QB-fork dependency pins remain distinct compatibility questions.
- First GPU attempts exposed observer double-decoding, unavailable AWS capacity and incorrect conversion of CUDA-Q SampleResult. The successful code uses `.items()`. Failed attempts and cleanup are retained in the feasibility directory rather than discarded.
- EC2 console timestamps can corrupt long JSON lines. Two retained copies were normalized and compared; subsequent adapter evidence used bounded hashed chunks. See the console parser and regression tests in [gpu_adapter](../gpu_adapter).
- The first microVM bootstrap hit an already mounted `/dev`; the failed boot and corrected retry are retained. Successful workloads were stopped by the supervisor after their marker, not proven graceful guest shutdown.
- A successful result does not prove resource release. GPU process presence before each fault and absence after container removal were checked separately, followed by a fresh successful run. Temporary cloud resources were deleted and verified in the retained cleanup records.
- Workload hashes and counts are candidate observations. Only platform-owned admission, identity and acceptance can turn them into an authoritative hosted result. Neither synthetic replay nor Docker process cleanup supplies that authority.

## Issue map and bounded follow-ups

Use the existing platform issue tracker; issues are disabled in the public Qristal fork. Preserve old descriptions as historical context, with dated corrections rather than silently treating them as current designs.

| Existing issue | Scope to retain / bounded next work |
|---|---|
| [#1701](https://github.com/marqov-dev/marqov-platform/issues/1701) | Umbrella and current evidence index; capability-specific qualification, not restoration of the poll-loop worker |
| [#691](https://github.com/marqov-dev/marqov-platform/issues/691) | Published candidate native qualification retained; resource-ID persistence and corrected native recovery retained; next corrected-version soak, then owner-reviewed hosted profile |
| [#338](https://github.com/marqov-dev/marqov-platform/issues/338), [#2104](https://github.com/marqov-dev/marqov-platform/pull/2104) | Owner-reviewed isolated material/result integration; no competing executor or authority schema |
| [#609](https://github.com/marqov-dev/marqov-platform/issues/609), [#640](https://github.com/marqov-dev/marqov-platform/issues/640) | Build/target QA, reproducible native matrices, wrong-target and missing-output regressions |
| [#704](https://github.com/marqov-dev/marqov-platform/issues/704) | Actual deployed end-to-end test only after admission exists; local evidence does not close this |
| [#1585](https://github.com/marqov-dev/marqov-platform/issues/1585), [#1839](https://github.com/marqov-dev/marqov-platform/issues/1839) | Replace unsupported Python/dependency bypasses with independently pinned workload dependencies |
| [#1284](https://github.com/marqov-dev/marqov-platform/issues/1284), [#1334](https://github.com/marqov-dev/marqov-platform/issues/1334) | Historical image and catalog incidents; recheck current source before repeating claims, no availability flip from standalone proof |
| [#610](https://github.com/marqov-dev/marqov-platform/issues/610), [#613](https://github.com/marqov-dev/marqov-platform/issues/613), [#615](https://github.com/marqov-dev/marqov-platform/issues/615) | Noise and mitigation: forward sweeps and independent held-out correction now have bounded simulation evidence; drift, correlated readout and full SPAM remain unqualified |
| [#608](https://github.com/marqov-dev/marqov-platform/issues/608) | Cross-executor logical bit-order and shot-accounting conformance |

No issue is closed or capability marked complete by this record. QB work stays independent of the SDK/compiler release critical path.

## Conference project and figures

[Marqov workspace](https://app.marqov.ai/projects/776ca156-9051-4fcb-8aca-202e78a94cac/workspace) · [Report](https://app.marqov.ai/projects/776ca156-9051-4fcb-8aca-202e78a94cac/report).

`plot.py` reads the retained CPU-method and GPU-feasibility records. Run `python3 qualification/conference/plot.py` in an environment with Matplotlib. It performs no simulation, network call or cloud execution. `provenance.json` binds both raw inputs; `observations.csv` preserves exact counts, program hashes and derived intervals. PNG/SVG are suitable for the project/report. Pointwise Wilson intervals describe shot sampling only; shared seeds do not constitute independent repetitions. The two all-zero probabilities are marginal summaries, not entanglement certification. No unexpected outcomes were observed in these fixtures.

Suggested five-minute demonstration:

1. Open the research question and installed-source evidence: what can a community-maintained runtime provide?
2. Show the asymmetric readout chart, then the new parameter-sweep heatmaps in Experiment 7. Explain how symmetric errors reduce correlations and asymmetric errors also bias outcomes; each plotted setting includes its analytic expectation.
3. Show Experiment 8’s held-out correction chart, including the wider uncertainty at strong noise. Then show `cpu-gpu-correlations.png`: the same circuit family across five methods. Explain why correct counts and logical bit ordering precede speed claims.
4. Open the GPU fault/recovery evidence: cancellation and cleanup are part of a useful platform, not merely launching a simulator.
5. Discuss next work and partnership possibilities. Saved experiments are explicitly labelled; do not click unavailable backends or imply QB endorsement.

Next experiment ideas, in priority order:

- **Packaged GPU repeat — passed:** [retained evidence](../evidence/2026-09-11-gpu-package) covers both targets, no source overlay, derivative identity, negatives and fault/recovery. The retained private registry artifact now also passed [native qualification](../evidence/2026-09-11-gpu-published); hosted integration and public distribution review remain separate.
- **Readout sweep — passed:** [source and analytic checks](../readout_sweep), [raw observations](../evidence/2026-09-11-readout-sweep), and [heatmaps/CSV](readout-sweep). All 50 native cases passed; the maximum outcome-probability residual was 0.004931640625 against the predeclared 0.025 tolerance. The seed-42 heatmaps show discrete measured settings, with analytic expectations in each cell. Both seeds remain in CSV. The subsequent held-out correction result is recorded below.
- **Structure-sensitive scaling:** GHZ versus more entangling circuits, increasing qubit count with explicit time/memory ceilings. Record warm-up/compilation separately, repeated timings, failures and truncation settings. No speed comparison until hardware and measurement protocol are controlled.
- **Mitigation demonstration — passed under the restricted model:** [protocol](../readout_mitigation), [26 native calibration/held-out cases](../evidence/2026-09-12-readout-mitigation), [before/after chart](readout-mitigation). All three accepted settings improved; the singular control was rejected. Next: test calibration drift/model mismatch and repeat calibration to study coverage before broadening claims.

Potential article outline: inaccessible legacy dependencies → reproducible public subset → analytic correctness and bit order → CPU/GPU alternatives → failure and recovery evidence → isolated execution boundary → open maintenance and partnership roadmap. Cite source commits and raw observations for each claim; do not turn bounded experiments into universal performance or security claims.

## Maintenance handoff

[Supported subset, dependencies and release gates](../MAINTENANCE.md) · [Conference walkthrough and questions](WALKTHROUGH.md).

The [40-case drift protocol](../readout_drift/README.md) is committed; four offline tests pass. Native drift execution remains pending. The consolidated dependency-free replay passed 124 tests across nine suites. This is evidence replay, not a new CPU/GPU experiment. PR18 is merged; the platform execution boundary remains separate.

## Synthetic uncertainty follow-up

[Repeated-calibration study](../readout_coverage/README.md):
10,000 synthetic calibration/measurement repetitions, separate from Qristal
execution. Stationary interval coverage ranged94.3–96.5%; stale calibration
produced0/1000 coverage per fixture in both chosen mismatch scenarios.
[Counts and limitations](../evidence/2026-09-12-readout-coverage/README.md) ·
[Coverage chart](readout-coverage).
This illustrates why sampling intervals cannot cover systematic calibration bias.
The medium/Bell stationary Wilson interval excludes nominal95%; no thresholds
were tuned and no blanket coverage claim is made. The native drift run is pending.
