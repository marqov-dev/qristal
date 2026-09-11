# Hosted GPU profile review — 11 September 2026

**Recommendation for review:** retain the public CUDA-Q workload adapter and
qualify a fresh, single-attempt EC2 GPU VM as the first hosted isolation profile.
Reserve the whole GPU and VM, then terminate the VM after the attempt; do not
reuse a Docker host between Marqov tenants. Keep hosted admission disabled until
the authority, transport and resource-lifecycle gates below pass. This is a review
proposal, not an accepted profile, deployment template or new control protocol.

The public adapter is useful; the historical QB GPU worker image need not return.
Core/CUDA-Q bridge compatibility remains separate. The native tests establish
small-circuit execution and local GPU-context cleanup, not a hosted service.

## Inspected revisions and evidence

- Qristal main: `37d52e48c8c652de91bb0e965eb642915e33e5c3` (merged PR #11).
- Platform main: `551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5` (GitHub and local remote ref agreed).
- The active shared platform checkout was on a different branch/revision and was
  left untouched. Source findings below do not assert deployed behavior.
- [Native adapter and lifecycle evidence](../evidence/2026-09-11-gpu-adapter/README.md):
  twelve adapter circuits, three context-holding faults and fresh recovery passed;
  the temporary host, root volume and security group were deleted and verified.

## Concrete integration gaps

All platform links in this table pin the inspected source, rather than moving main.

| Existing boundary | Finding and required review |
| --- | --- |
| [Placement/resources schema](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/platform/src/lib/execution/contracts/execution-v1.schema.json#L98) | Compute classes are `cpu`/`quantum`; closed resources contain CPU, memory and timeout, without GPU quantity/model/memory. Agree a versioned GPU extension and reservation semantics; do not label GPU as CPU or smuggle new fields through an old version. |
| [Task material assembler](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/platform/src/task_materials.py#L103) | Python runtime/package/entrypoint and `python-value/v1` output are exact checks. Quantum-program syntax in the common schema does not admit this workload. |
| [Dispatch profile](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/platform/src/task_dispatch.py#L60) | Provider command fixes Fargate 1.4.0. Replacing only the image cannot supply a GPU. |
| [Runtime identity resolver](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/platform/src/task_runtime_evidence.py#L159) | Python execution plane/acquisition, ECS provider handle and Fargate command are explicit gates. An EC2 VM must have its own reviewed provider identity and authenticated binding; never fabricate an ECS task ARN. |
| [Result gateway](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/platform/src/task_result.py#L1) | Fresh submission authenticates runtime before authority reads; SQL ACK accepts the result. Receipt validation requires `python-value/v1`. GPU candidate JSON cannot directly become an execution receipt. Preserve exact historical recovery separately from fresh promotion authority. |
| [Existing CPU counts proposal](https://github.com/marqov-dev/marqov-platform/blob/551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5/tests/proposals/qb_v2/counts-candidate.schema.json) | This is a dormant experimental proposal with backend fixed to `qpp`, extra authority/preparation bindings and a positional map. Do not rename a GPU record to that schema or treat it as accepted. |

## Placement and isolation choice

AWS says GPU workloads are not supported on Fargate; ECS GPU scheduling uses
GPU-capable EC2 container instances. [Fargate FAQ](https://aws.amazon.com/fargate/faqs/),
[ECS GPU documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-gpu.html).
AWS also states that EC2-hosted ECS tasks do not provide a task isolation boundary
and can expose co-located credentials/data. A task role does not turn containers
into that boundary. [ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html).

| Option | Review conclusion |
| --- | --- |
| Existing Fargate profile plus GPU image | Unsupported hardware path and wrong admitted contract. Reject. |
| Shared ECS-on-EC2 or shared Docker GPU fleet | GPU scheduling is possible, but inter-tenant host/driver/credential isolation and reuse are unqualified. Defer. |
| Fresh EC2 GPU VM per attempt, external controller | Recommended first qualification target. Closest to observed hardware, no application-level tenant co-location or host reuse; requires a reviewed EC2 identity/lifecycle/transport adapter. Higher startup and whole-VM cost. |
| ECS-on-EC2 with one fresh VM per attempt | Plausible later variant for ECS task identity; still needs VM ownership, host cleanup, credential isolation and EC2-specific identity checks. More resources to reconcile; no automatic reuse of Fargate qualification. |

“Single-attempt VM” describes Marqov scheduling, not AWS Dedicated Instance tenancy
or a claim of dedicated physical hardware. VM replacement reduces Marqov's own
reuse surface; it does not independently prove AWS GPU reset/sanitization or
hardware isolation. Review the provider boundary before accepting hostile tenants.
The successful CPU Firecracker proof supplies no GPU passthrough evidence.

## Proposed first resource cell (unregistered)

| Aspect | Proposed bound and remaining evidence |
| --- | --- |
| Workload | Existing `qristal.cudaq-circuit/v1` data artifact; X/H/CX only, final full measurement, 1–12 qubits, 1–256 gates, 1–16,384 shots, bounded seed. No arbitrary Python or commercial Emulator. |
| Target | Separate allowlisted state-vector/fp64 and tensor-network placements. Artifact `target` must equal admitted placement before launch and again at execution. The current CLI alone does not establish that agreement. |
| Hardware | One g5.xlarge/A10G per attempt in the reviewed region; no fractional GPU, MPS sharing or concurrent tenant jobs. This matches qualification hardware, not a capacity/performance promise. |
| Reservations | Reserve the full VM (4 vCPU / 16 GiB host RAM), one entire GPU and associated disk lifetime. Workload cgroup: 4 CPU / 12 GiB RAM. Docker memory limits do not impose a VRAM quota; reserve the whole device rather than promise a smaller enforced quota. |
| Runtime | Published derivative manifest binding adapter, CUDA-Q image, dependency inventory and configuration; immutable boot AMI/kernel/driver/container-runtime identities separately bound. The tested source overlay plus upstream digest is not yet a published derivative release. |
| Local workload controls | Non-root, read-only root/input, 512 MiB bounded executable scratch, 512 PIDs, dropped capabilities, bounded logs, no workload network or provider credentials. Hosted equivalents must be demonstrated, not copied as comments. |
| Time/output | Workload deadline at most 120 seconds; candidate stdout at most 128 KiB and stderr 16 KiB, as tested. Separate VM startup/teardown deadlines and reservations; the one-hour experiment cap is not a hosted SLA. |
| Attempt/retry | One authorized computation attempt initially. An uncertain launch recovers the exact retained provider identity; transport retry must not create a second VM or rerun computation. |
| Teardown | No reuse, stop/start retention or warm pooling. Terminate the exact VM, verify terminal provider state and delete owned disks/other resources. Reconcile failed cleanup independently of accepted result state. |

The VM itself is an untrusted workload boundary, including its kernel-facing GPU
stack. Put financial, admission and acceptance controllers outside it. Do not put
trusted controllers, provider credentials, broad account roles or other tenant
artifacts in the same VM. Network denial and no privileged mounts are additional
controls, not proof against a GPU-driver escape.

**Transport/identity gate remains open:** the experiment used operator-supplied
inputs and AWS console chunks. That is not accepted hosted task-material delivery
or runtime attestation. Review a credential-minimal material/result transport,
its freshness and attempt binding, and independent runtime authentication before
any authority read. If result extraction uses a disk or archive, parse it inside
an isolated reader; never mount an untrusted guest filesystem in a trusted service.
No choice of transport is silently established by this proposal.

## Candidate-to-platform mapping

1. Resolve accepted program/input artifacts through existing authority. Bind their
   exact bytes, the requested simulator, runtime profile/lock and task request.
   The first profile either accepts this typed circuit format explicitly or uses
   a separately qualified isolated conversion. No arbitrary QASM-to-JSON conversion
   is implied by the current gate-list adapter.
2. Keep `qristal.cudaq-candidate/v1` as unaccepted workload output. Bound parsing
   must reject duplicate/extra keys, missing output, wrong target/version/source
   or input hash, invalid count types/widths and shot-total mismatches. Validate
   against independently acquired expected context, not the candidate's own claims.
3. Preserve counts and an explicit position-to-logical-bit map. For this full
   measurement cell, position i is q[i]; a trusted reviewed transformation can
   construct that identity map from the accepted artifact. Do not infer a physical
   device mapping or silently reuse Braket-specific fields.
4. Review a provider-neutral sampling output schema with requested/successful/
   discarded/unknown shot accounting, separate from runtime provenance. Complete
   success has total counts equal requested shots; failure emits no successful
   counts artifact. Keep the candidate bytes and their digest for independent audit.
5. Bind accepted request/attempt/operation, exact provider acquisition and runtime
   evidence through the existing authorized acceptance writer. Candidate image and
   adapter hashes are claims until checked against trusted expected identity.
   Never let the workload mint authority IDs, receipts, cost settlement or engine state.

Direct and Temporal paths must use the same accepted material, adapter and receipt
semantics. This review proposes no engine-specific executor or competing envelope.

## Qualification gates and bounded follow-ups

| Gate | Smallest next work and acceptance evidence |
| --- | --- |
| Mapping | Offline proposal fixtures using retained native candidate bytes plus independent synthetic admitted context. Reject changed target/input/runtime, missing/extra output and reversed bit maps; direct/Temporal produce identical candidate validation. No database acceptance or GPU required. |
| Packaging | Build and inventory a derivative image in an isolated build lane, qualify without source overlays, review distribution licenses/SBOM and pin both workload and boot/runtime identities. GPU execution must retain the native matrix; a build alone is insufficient. |
| Provider lifecycle | Review EC2 acquisition/identity, idempotency and spend/capacity binding with the execution owner. Cover lost launch ACK, duplicate dispatch, stale ownership, result-before-stop, stop-before-result and restart recovery. No real launch until the reviewed authority path exists. |
| Isolation | Separate authorized single-attempt VM experiment: material/credential isolation, authenticated result transport, long-kernel timeout, controller loss and exact provider terminal observation. Also verify workload completion cannot release host capacity. |
| Admission | Owner accepts the versioned contracts/profile and negative fixtures; register an initially restricted cohort only after deployment checks. UI availability and hosted job/result display must follow real accepted evidence. |

**Next task recommended now: the offline mapping review fixtures.** It resolves
contract uncertainty without new infrastructure or paid runs. Packaging can progress in
an independent lane; provider lifecycle and isolation depend on owner review. Reuse platform #691
for historical GPU context, #2027/#2028 for the common-contract programme and
#2104 for the related QB profile discussion; close none on this review alone.

The release owner retains the profile/contract decision. Nothing here adds a
release-critical dependency, changes a shared checkout, starts a service, registers
a backend or claims the main agent has accepted hosted GPU admission.

## Offline mapping follow-up

The [mapping experiment](../gpu_mapping/README.md) now supplies the proposed
offline fixtures: twelve retained GPU candidates replay against independently
constructed circuit/runtime expectations, with twelve regression tests. Synthetic
engine-label parity and local display previews do not accept a hosted contract.
Packaging, provider lifecycle, identity/transport and isolation remain open.
