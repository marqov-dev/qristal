# Community qualification

This is a separate qualification effort, not a supported release or a platform dependency.
The public Qristal 1.8.1 sources are the baseline. Commercial Emulator and internal vQPU services are outside scope.

| Component | Acceptance evidence required | Current status |
|---|---|---|
| Public toolchain | Public base digest, package inventory; no QB binary inputs | Built from Ubuntu 22.04; package inventory recorded locally |
| XACC/qpp | Fresh compile, ACZ registration and interference tests, Bell correlations | Passed on public Ubuntu toolchain: five runtime fixtures; installation passed |
| Core | Link/import rebuilt Python extension; ideal circuits, bit ordering, shot conservation; separate noise fixtures | Passed for eight ideal CPU fixtures, including OpenQASM and optimizer paths; noise pending |
| Decoder | Build both plugins; known small inputs and invalid-input tests | Pending; requires Core |
| Integrations | Version-compatible Qiskit sampler/estimator; parameters, observables, measurements and application examples | Pending; Core pins Qiskit 0.46 but integrations expect 1.2.0 |
| SDK distribution | Build pinned components, install into fresh runtime, run own examples without source tree | Pending |
| Tensor networks | Public ExaTN/TNQVM build; exact small-circuit comparisons and truncation checks | Pending, excluded from initial CPU profile |
| GPU | Explicit GPU/backend versions, native GPU correctness and resource tests | Pending; no GPU or paid execution authorized |
| Managed execution | Adapter contract, isolated job lifecycle and result retrieval | Later; outside current platform/compiler release critical path |

Acceptance requires logs, exact source revisions, dependency versions, test counts and limitations. Compilation or import alone is not evidence that a simulator works. Statistical tests must specify sample sizes and tolerances in advance. Unsupported backends must not silently fall back to another simulator.
