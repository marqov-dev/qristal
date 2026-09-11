# Community qualification

This is a separate qualification effort, not a supported release or a platform dependency.
The public Qristal 1.8.1 sources are the baseline. Commercial Emulator and internal vQPU services are outside scope.

| Component | Acceptance evidence required | Current status |
|---|---|---|
| Public toolchain | Public base digest, package inventory; no QB binary inputs | Built from Ubuntu 22.04; package inventory recorded locally |
| XACC/qpp | Fresh compile, ACZ registration and interference tests, Bell correlations | Passed on public Ubuntu toolchain: five runtime fixtures; installation passed |
| Core | Link/import rebuilt Python extension; ideal circuits, bit ordering, shot conservation; separate noise fixtures | Passed for eight ideal CPU fixtures, including OpenQASM and optimizer paths; ten CPU Aer fixtures also pass (ideal controls, readout, amplitude damping, depolarizing noise) |
| Decoder | Build both plugins; known small inputs and invalid-input tests | Installed simplified-decoder consumer passed nine fixed fixtures; full quantum-decoder execution remains unqualified ([installed evidence](installed/README.md)) |
| Integrations | Version-compatible Qiskit sampler/estimator; parameters, observables, measurements and application examples | Sixteen Qiskit 1.2 V1 checks passed in a separate dependency environment; Core parser retains Qiskit 0.46. V2 and general application semantics remain unqualified ([installed evidence](installed/README.md)) |
| SDK distribution | Build pinned components, install into fresh runtime, run own examples without source tree | Installed-only CPU and local pinned image qualified; registry publication, relocatable packages and supported distribution remain pending ([runtime guide](runtime/README.md)) |
| Tensor networks | Explicit method selection; exact small-circuit comparisons and truncation checks | Aer CPU MPS passed six analytic fixtures; public ExaTN/TNQVM reconstruction and truncation checks remain pending |
| GPU | Explicit GPU/backend versions, native GPU correctness and resource tests | Standalone CUDA-Q 0.15 state-vector and tensor-network targets passed twelve native A10G cases; Qristal Core integration and hosted execution remain unqualified |
| Managed execution | Adapter contract, isolated job lifecycle and result retrieval | Later; outside current platform/compiler release critical path |

Acceptance requires logs, exact source revisions, dependency versions, test counts and limitations. Compilation or import alone is not evidence that a simulator works. Statistical tests must specify sample sizes and tolerances in advance. Unsupported backends must not silently fall back to another simulator.

A subsequent [bounded CPU/KVM proof](microvm/README.md) passed fixed preparation,
validation, qpp sampling, forced termination and output-overflow cases. This adds
native guest feasibility evidence only; it does not change the managed-execution,
GPU or broader VM backend qualification statuses above.

The restricted CPU parser pipeline also now exposes Aer readout noise on qubit zero:
27 regression/boundary methods and 11 analytic native cases pass, with eight offline
evidence-checker tests. See [the readout evidence](evidence/2026-09-11-readout-pipeline/README.md).
This is a source overlay on the existing local image, not a newly published image,
full device emulator, SPAM mitigation or hosted backend. The platform's independent
local QPP rehearsal is merged; production admission, lifecycle and availability
remain outside this community qualification status.
