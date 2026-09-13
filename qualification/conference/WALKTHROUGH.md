# Quantum Brilliance conference demonstration

Use the saved [report](https://app.marqov.ai/projects/776ca156-9051-4fcb-8aca-202e78a94cac/report).
Open it before the meeting. No live cloud job or backend selection is needed.

## Five-minute sequence

**0:00 — The question.** “We explored which public Qristal capabilities could be
maintained and presented through a heterogeneous research platform.”

**0:30 — CPU foundation.** Show the public-source/installed evidence. Explain that
the selected runtime works without the missing QB binary dependencies. Be precise:
Core, Integrations and simplified Decoder fixtures are tested, not all features.

**1:15 — Noise you can inspect.** Open Experiment7's parameter-sweep heatmaps.
Increasing symmetric readout error reduces measured correlations; asymmetric error
also changes the balance of outcomes. The plotted data are actual saved simulations.

**2:00 — Calibration improves the estimates.** Open Experiment8. Calibration
measurements are separate from held-out circuit samples. The three tested settings
show roughly96% reduction in aggregate observable error. Explain the wider error
bars under strong noise and the rejection of an unstable calibration. This is a
restricted classical readout model, not a claim about physical QB hardware.

**2:40 — Calibration can go stale.** Show the native drift chart. Fresh correction
reduced aggregate error by approximately 95–98%; stale correction worsened two
settings, reaching 4.45 times the raw error when the underlying noise improved.
Distinguish this 40-case native experiment from the separate synthetic coverage study.

**3:20 — CPU and GPU alternatives.** Show Bell/GHZ across five methods. Three CPU
methods and two standalone CUDA-Q GPU targets passed small-circuit correctness.
The GPU used A10G; these charts do not compare speed or establish maximum capacity.

**4:00 — Engineering needed around a simulator.** Show Experiment6's artifact
identity and recovery record. Work includes reliable packaging, candidate validation,
bounded execution and cleanup. Hosted integration is a separate next phase.

**4:30 — Partnership discussion.** Ask what examples and maintenance boundaries
would be useful to QB and its users. Potential cooperation includes upstream
feedback, public examples, hardware comparisons and later commercial-plugin access.
No partnership or endorsement exists merely because this report exists.

## Answers to likely questions

- **Did you recreate the commercial Emulator?** No. Public CPU components and
  public upstream GPU alternatives are distinct from that product.
- **Is this the original GPU integration?** The demonstrated GPU runtime is
  standalone CUDA-Q, not qualification of the old Core bridge.
- **Can I run it on Marqov now?** This report contains saved experiments. Hosted
  admission and result acceptance are not yet enabled by this work.
- **Can you maintain it?** The evidence supports a bounded subset. The maintenance
  plan defines release gates, dependency responsibilities and unqualified paths.
- **What is next scientifically?** The 40-case native calibration-drift experiment
  is complete. Next are repeated native calibrations, model mismatch and carefully
  scoped scaling measurements.
- **Is everything Apache2?** The public forks and the entire assembled runtime
  are different licensing scopes. Dependency notices and distribution review matter.

## Backup and article material

The versioned conference directory contains PNG/SVG figures and provenance.
Keep the retained experiment links next to each claim. The report itself can be
shown without launching compute. Export the self-contained five-chart HTML and
allowlisted evidence ZIP using [the packet instructions](packet/README.md); run
the archive verifier after copying. Embedded figures need no network.

Optional technical appendix: 70 native QFT/IQFT complex-state checks passed at
1–3 qubits. Show the numerical table and saved vector provenance in the report.
Full Decoder still times out in its first search iteration; service restoration
and QFT correctness do not establish a completed Decoder result.

Tracking: platform #2172 (conference), #2173 (full Decoder), #1701 (priority queue).

Article outline: public dependency recovery; installed-only evidence; analytic noise
tests; independent mitigation and uncertainty; public GPU alternatives; packaging
and observer failures; bounded support and a future hosted integration.

Preserve distinctions between successful native execution, offline replay, planned
experiments and deployed behavior throughout the article. Avoid speedup, full-SPAM,
hardware-fidelity or maximum-qubit claims unsupported by the saved observations.
