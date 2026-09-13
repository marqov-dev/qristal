# Hosted QB integration — current source gap assessment

David prioritised packaging and hosted execution over full Decoder on 13 September
2026. The release owner requested this independent read-only assessment while the
hosted Python canary and Project/Report persistence milestone complete. This does
not authorise a profile substitution or establish deployed QB availability.

Inspected platform **22f12a9ff6b7ec06257b77d0baf1d02f14ad05f2** in an isolated
checkout. The shared platform checkout was on unrelated branch codex/alicebob at
3cb28c9b0bdde9500ffca0d0f64bf17b67bdeba3 and was not changed. Qristal baseline:
**49892dde6d6b5be778e965121c99932d8e016bd1**. Findings below concern source and
retained standalone evidence; no live admission/database/provider inspection ran.

## Available packages and first integration target

CPU candidate:
`ghcr.io/marqov-dev/qristal-cpu@sha256:c500987ef91ab0e0d3dd32ea75436785308ae1603c221762291d9c13dff431c5`.
Its acquired-image matrix passed 43 functional fixtures. It exposes a restricted
OpenQASM sampling CLI using Python 3.10/native libraries and local experimental
counts JSON. It is not the SDK 0.7/Python 3.12.14/cloudpickle task image.

GPU candidate:
`ghcr.io/marqov-dev/qristal-cudaq-gpu@sha256:ecb6923fa1465650453de810c938eb949f809abbc1361831f0e0e14d84e95409`.
A10G standalone state-vector/tensor-network, fault and recovery tests passed.
This is a distinct NVIDIA CUDA-Q adapter, not the original Core/GPU bridge.
GPU execution ownership/topology is not established by the current release task.

Recommend first admitting a closed CPU/QPP circuit-sampling cell, with Aer and
noise expanded only through their explicit tested contracts. This is a proposal
for owner decision; do not restore old worker polling or label it deployed.

## Concrete gaps and required evidence

All platform paths below refer to the inspected SHA above.

| Boundary | Current implementation | Required QB work |
|---|---|---|
| Semantic admission | `platform/src/execution_contract.py:205` equates quantum_program with quantum compute placement. Existing v1 binds compiler and task runtime identity. | Explicit versioned compatibility tuple for quantum simulation on CPU, with separately admitted compiler/preparation/task identities. Preserve v1 rejection; dormant QB fixtures are not admission. |
| Exact image and lock | `platform/src/task_materials.py:103` requires python-compiler-v1, exact image and dependencies/v1 digest. CPU package Dockerfile selects a different ABI and CLI. | Reviewed operator-owned QB manifest/lock/profile, including registry index versus platform manifest representation. No arbitrary image chosen by compiler or tenant. Inventory/SBOM is not automatically the admitted lock artifact. |
| Assignment and materials | `platform/src/task_delivery.py:75` authenticates/binds retrieval and obtains final authority acknowledgement; manifest/file retrieval rechecks current authority. `task_gateway_client.py:391` accepts only Python package/value schemas. | Closed QASM/options/canonical-program/bit-map material shape, independently bound preparation, current claim checks and immutable staging. Reuse authority order, not Python labels. |
| Native execution isolation | Existing task bootstrap/entrypoint carries Python-specific delivery and result protocol. Standalone QB candidate has no such bootstrap. | Approved separation between credential-bearing delivery and networkless native parsing/simulation, including metadata/process/filesystem isolation and enforceable CPU/memory/PID/output limits. Same-role ordinary sidecar is not proof. |
| Dispatch and execution claims | `task_dispatch.py:15` fixes python-task-v1. `task_runtime_evidence.py:172,193,217` fixes Python execution plane, acquisition tuple and FARGATE command; image binding derives from admitted intent. | Explicit QB acquisition/profile and independently observed runtime identity with durable command-before-dispatch, unknown-outcome recovery, claim fencing and no duplicate execution on upload retry. |
| Result acceptance | `task_result.py:133` requires python-value/v1; `task_display.py` validates bounded inert display separately. QB candidate.py validates content only. | Reviewed provider-neutral counts result and receipt binding: program/options/backend, shots, bit map, attempt/request/runtime identity. Workload JSON cannot issue authoritative success; no fabricated Braket task ARN. |
| Project and Report | Python result/display receipts support the current native canary. The QB report currently contains saved standalone experiments. | Actual accepted QB job result retrievable under tenant scope, persisted in Project and rendered from accepted display/artifact data. Do not retroactively describe saved experiments as hosted jobs. |
| Stop, cleanup and money | `task_stop_provider.py:5` separates StopTask acceptance from STOPPED proof; task_resource_release and task_controller own release/recovery. | Native QB cancellation/timeout/lost acknowledgement/stale-result cases through the same durable authority. Independent terminal observation must precede resource release and applicable accounting; Docker removal alone is insufficient. |
| GPU | Current source binding demands Fargate; standalone evidence uses a dedicated A10G VM. | Owner-selected GPU execution plane, reservations, driver/runtime identity and host termination/isolation policy. CPU profile qualification does not cover this. |

Earlier proposal documents remain useful review inputs:
`docs-internal/plans/2026-09-09-qristal-hosted-cpu-profile-proposal.md`,
`2026-09-09-qb-task-runtime-contract-amendment.md`, and
`2026-09-09-qb-preparation-staging-topology.md`.
`tests/test_qb_dormant_contract.py` deliberately preserves live v1 rejection and
forbids production references to its reduced proposal validator. This assessment
rechecked the current source predicates rather than treating those proposals as
implemented hosting. No new tests or native jobs were run for this source review.

## Ownership and completion order

1. QB lane: finish source/install retention and dependency artifacts; preserve the
   already qualified immutable candidates and rerun acquired-image tests for any
   changed package. Full Decoder is not a prerequisite.
2. Release owner: after the active canary, decide versioned admission/result shape,
   task-runtime separation and native staging topology; assign GPU execution owner.
3. QB lane, after that decision: implement the bounded CPU adapter/material/result
   integration in an isolated branch with common contract regression tests.
4. Joint qualification: real hosted CPU job, tenant-scoped result retrieval and
   Project persistence; cancellation, timeout, recovery and authoritative release.
   Record exact deployed SHAs/image/lock and observed outcomes before claiming done.
5. Qualify GPU hosting separately with its agreed owner and the same customer
   result/lifecycle contract. Preserve engine identity for direct and Temporal.

Tracking: platform #338 for hosted integration, #1701 for programme priorities,
#609/#640/#1839 for packaging/qualification. Historical #338 speed claims and
in-process/thread-pool architecture are not supported or adopted by this review.
Keep internal planning in GitHub/workspace; the externally shared QB Report is a
curated results presentation already shared with Quantum Brilliance.
