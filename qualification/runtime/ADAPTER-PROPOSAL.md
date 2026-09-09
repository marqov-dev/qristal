# CPU runtime adapter proposal — not an accepted hosted contract

The release owner requested image evidence before reviewing an adapter. This document is that review input. It does not implement, freeze or replace a hosted wire protocol, connect old QB workers, or authorize a deployment.

Source reference: platform `898969ddd1fcec3a3e8290d5a0e3277823625470`, docs-internal/plans/2026-09-08-common-execution-contract.md, ADR-0016 and the release programme. Those documents remain living specifications. The release owner's follow-up explicitly required exact provider identity, fenced ownership, terminal proof and resource accounting for cancellation; a job row alone is insufficient.

## Proposed first cell

One admitted quantum-program task executes an immutable OpenQASM 2 artifact on the public CPU image's qpp or Aer backend. Optional readout-noise parameters are typed input-artifact data, not a device model. The image's local CLI is an isolated workload implementation detail. Neither its JSON output nor its exit code is a hosted receipt or customer-state authority.

| Boundary | Proposal for review |
|---|---|
| Admission and task identity | Reuse the accepted submission, plan, task attempt and operation identities. Neither CLI nor adapter mints them, selects an orchestration engine or grants authority. |
| Runtime identity | Allowlisted profile binds the published immutable OCI manifest digest and dependency-lock artifact. The current local image ID is evidence only; it is not a published registry manifest digest. |
| Input | Artifact resolver/attested runner verifies admitted program and input digests. Mount the resolved QASM artifact read-only inside the isolated workload. Do not add inline source or floating-point noise values to trusted control/history envelopes. |
| Capabilities | Initially qpp/Aer sampling only. Decoder and other libraries have qualification evidence but no advertised hosted operation in this proposal. No GPU, provider credentials, arbitrary tenant Python entrypoint or commercial Emulator. |
| Bounds | The profile ceiling is 12 qubits, 16,384 shots and 64 KiB QASM. Admission may authorize less. Controller enforces admitted CPU/memory, output bytes and an outer deadline; these image defaults are not grants. No network, non-root user, read-only filesystem and bounded scratch space. |
| Dispatch and retries | Existing fenced acquisition/dispatch authority creates or recovers one exact provider task/container identity for the committed operation. A transport retry cannot silently rerun computation; task attempts remain database-authorized. |
| Result | Isolated runner emits a bounded candidate result artifact with counts, explicit qubit-0-first ordering and program digest. Bind it to admitted task/runtime/operation provenance. Existing trusted validation/promotion produces the authoritative receipt; stdout is not promoted by trust alone. |
| Failure | Preserve process/parser/timeout/unknown-dispatch observations. The controller decides authoritative outcome and retention through existing fenced writers. CLI failure does not release a reservation or acquisition. |
| Cancellation | Follow admitted cancellation policy and fenced ownership; stop the exact recorded provider identity, obtain independent terminal/stopped proof, then perform authorized resource release. A local docker stop experiment would not qualify hosted cancellation. |
| Orchestration | The same task adapter serves direct and Temporal paths through their shared contract; no engine-specific worker or database writer is added here. |

## Decisions needed from the execution-contract owner

1. Confirm the current quantum-program artifact/media schema and supported canonical result schema for this first CPU cell.
2. Select the runtime-profile registration, attested-runner entrypoint and provider resource-acquisition adapter where this belongs.
3. Confirm the existing attempt/result-promotion and cancellation fixtures this adapter must satisfy; then add CPU-specific positive/negative fixtures alongside them.

The narrow local CLI is deliberately provisional. It performs workload checks inside isolation; it is not an authorization validator. Its input parsing does not replace trusted artifact binding, outer resource enforcement or the platform's canonical schema validation.

No SDK/compiler release dependency is established. Proposed implementation follows owner review and remains separate from the current compiler-recovery work.
