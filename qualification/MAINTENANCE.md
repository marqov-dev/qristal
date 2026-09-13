# Maintained simulation subset and release gates

Current status baseline: Qristal mainbb1ccc1601ce6962101cfa87f2c44d4f7ffebc91
(merged PR36, 13 September 2026), plus its successful CPU publication run34743836599. Historical native evidence retains its original revisions.
This document defines the proposed maintenance scope, not a supported release.

## Repair, replace or retire

**CPU: replace the legacy worker image with the qualified public-source runtime.**
Retain useful QPP/Aer simulation, local noise and selected integration/decoder
capabilities. Do not restore the old poll-loop worker or SDK Python-version
bypasses. The rebuilt CPU runtime has installed-only and compiler-free image
evidence and now a private registry candidate with acquired-image checks, corrected
backend rejection and inventory export. Public distribution, original binary
build provenance and hosted admission remain separate gates. See the
[CPU publication evidence](evidence/2026-09-13-cpu-published/README.md).

**GPU: replace the legacy image with the qualified standalone CUDA-Q candidate.**
The published private candidate passed on A10G for nvidia fp64 and tensornet.
Retain those capabilities without claiming compatibility with the older Core
bridge or proprietary qb_mps target. Public distribution and hosted admission
are not established by a private image passing native tests.

Retire the old images from the proposed design after replacement integration and
migration decisions. This document does not delete images, change catalogs or
decommission deployments. Repairing their original implementation adds dependency
and orchestration burden without preserving an established working customer path.

| Path | Evidence we can maintain | Remaining support boundary |
|---|---|---|
| Core QPP ideal CPU | 8 installed Core fixtures; QASM, optimization, transpilation, result retrieval | Arbitrary circuits/API coverage and current Python ABI combinations |
| Aer CPU noise | 10 installed analytic noise fixtures; 11 restricted readout cases; 50-case sweep | Pulse/device models, correlated noise and general SPAM |
| Aer MPS / density matrix | 6 circuits each on explicitly selected methods | Scaling, truncation semantics, performance and broader circuit families |
| Integrations | 16 Qiskit 1.2 V1 checks, separate installed environment | Package distribution, V2, broader measurement/options semantics |
| Decoder | 9 simplified fixtures on qpp/Aer/sparse-sim; installed C++ consumer; 6 current XACC-linked initialization tests passed in isolated CPU VMs | Full algorithm and caller-result correctness unqualified; native dependency diagnostics retained separately |
| Public QFT/IQFT provider | 70 QPP complex-state fixtures, all basis inputs at 1–3 qubits; independent Fourier and round-trip checks | Qualification-only subset, not the full generators bundle; shifted registers, other sizes/backends and invalid inputs unqualified |
| Readout mitigation | 26 native mitigation cases plus 40 native drift cases, independent calibration, signed correction | Broader drift, repeated native calibration, preparation/model mismatch |
| Standalone CUDA-Q GPU | A10G nvidia fp64/tensornet, private published candidate | Other GPU/driver combinations, scale, long-kernel termination |
| Core/CUDA-Q bridge | Source compatibility question | No native bridge proof; do not substitute standalone evidence |
| ExaTN/TNQVM | Excluded from CPU qualification | Public reconstruction and native correctness not established |
| Hosted CPU/GPU | Offline mapping and CPU VM feasibility | Platform-owned identity, admission, transport, acceptance and lifecycle |

Sources: [installed](installed/README.md), [runtime](runtime/README.md),
[methods](accelerators/README.md), [GPU publication](evidence/2026-09-11-gpu-published/README.md),
[mitigation](readout_mitigation/README.md), [conference ledger](conference/README.md).

The September 12 [CPU cloud diagnostics](full_decoder/cloud/README.md) separate
native compilation, service registration, result semantics and resource cleanup.
They identified a missing post-link bundle step in our new harness, then an
omitted public XACC QFT dependency in the selected installed prefix. The original
failed attempts remain evidence. Neither problem establishes a need for private
QB code; neither justifies claiming the complete Decoder works. Restoration of a
required service must still be followed by an independent mathematical check.

That check now [passes for the public QFT/IQFT subset](evidence/2026-09-12-qft-states/README.md).
The bounded Decoder trace confirms service availability and entry into search
iteration 1, but still times out before a result. A source audit identifies
eager many-controlled-Z decomposition as a hypothesis. The subsequent
[trace-only native probe](evidence/2026-09-12-search-trace/README.md) locates the
timeout inside an 18-control Z expansion, before backend execution. Its internal
CPU/allocation cost and a full-fixture repair remain unqualified.
The [controlled-Z prototype](evidence/2026-09-12-mcz-equivalence/README.md) now
passes 42 complex-state cases, 158 sparse interference cases and 10 input
rejections after an initial enabled-state failure. This is an internal prototype,
not a generic Circuit API or production Core change. Its scope/mapping limitations
and remaining integration gates are explicit. The subsequent
[full-fixture derivative](evidence/2026-09-12-mcz-decoder/README.md) completes MCZ
construction and one backend sample, then times out during a second backend call.
The first backend call took about 34.6 seconds; no caller-result completion is
claimed. The subsequent [backend profile](evidence/2026-09-12-backend-profile/README.md)
locates about 18.7 seconds in inverse preparation and 18.0 seconds across the two
forward-preparation passes, with only 0.313 ms in sampling. Almost all elapsed
backend time is within visitor calls, including deferred simulator work. The
full caller fixture still times out; structure-preserving inversion is a candidate,
but forward preparation also needs attention. Two failed reporting attempts and
all three exact cleanups are retained.

The [controlled inverse experiment](evidence/2026-09-13-structured-inverse/README.md)
adds 140 candidate complex-state cases, 20 direct sparse interference cases,
20 repeated sparse roundtrips and 12 input rejections. It caught our incorrect
assumption about QPP direct-control support, then four exact-phase discrepancies
in legacy controlled-Rx fallback. Those standalone discrepancies are global phase,
not demonstrated wrong probabilities or decoded results. The candidate uses
explicit QPP lowering; neither a full Decoder speedup nor generic IR compatibility
is established. [Preparation and phase audit](full_decoder/cloud/PREPARATION-AUDIT.md)
defines the next bounded work.

## Latest Decoder boundary and independent ownership

The [actual preparation inventory](evidence/2026-09-13-phase-composition/README.md)
finds only about a2% traversal difference for narrow controlled-block preservation.
The specific further-control phase experiment did not show an observable probability
error; do not infer a wrong decoded answer from the earlier global-phase mismatch.
The [stored-state probe](evidence/2026-09-13-sparse-state/README.md) passed observation
neutrality checks and sampled transient state growth. The
[O3 comparison](evidence/2026-09-13-sparse-state-o3/README.md) did not resolve the
60-second caller timeout. Both configurations remain diagnostic, not promoted runtimes.

Two independent Claude Code lanes now cover Decoder scientific research and targeted
engineering. Their future findings are subject to review and native qualification.
Full Decoder remains optional to the public simulator offering and platform release.
The coordinator owns the broader CPU/GPU subset, distribution and conference work.
Use [the current conference summary](conference/CURRENT.md) for the short account;
chronological findings above remain available as the investigation record.

## Dependencies and release policy

The selected CPU toolchain is Ubuntu 22.04, GCC11.4 and Python3.10.12/linux-amd64.
Core's Qiskit0.46 environment and Integrations' Qiskit1.2 environment are separate.
Neither is the host platform SDK environment. Keep these workloads behind the
execution boundary instead of relaxing SDK Python requirements.

The public source lock selects Core a5c3e5fa544c07d538974d3a289b19652d483848,
Integrations 16e4941ef5ad8476ad971a366ecce91e5ea5bd45,
Decoder 13bb8f80f98bd259196834a13817c23ec02480e6 and patched public XACC
d1edaa7ae53edc7e335f46d33160f93d6020aaa3. See source-lock.json and
python-constraints.txt for exact dependencies. These are tested selections,
not assertions that every dependency is current or receives upstream support.

The GPU candidate uses CUDA-Q0.15.0 and recorded NVIDIA runtime dependencies.
Its A10G observation used driver595.91.07. Registry index, platform manifest,
image configuration and archive hashes are different identities: preserve all
bindings; never equate a local Docker ID to a registry manifest by string alone.

Before a public supported distribution:

1. Acquire public source/dependencies in a clean dedicated workspace and retain
   immutable revisions, archive hashes, patch inventory and acquisition logs.
2. Build/install with source trees absent during installed-runtime checks.
   Snapshot package acquisition or explicitly retain the non-reproducibility gap.
3. Run native correctness and negative tests on every advertised runtime/ABI.
   Test the exact distributable image, not only a source overlay.
4. Retain SBOM, license/notice texts and provenance. Review each bundled dependency
   and redistribution path; the four Apache-licensed forks do not make NVIDIA,
   OS and other dependency contents Apache-licensed.
5. Publish a versioned candidate with an explicit experimental support matrix,
   reproduction commands and known limitations. Do not expose registry access
   instructions requiring private credentials in the conference report.
6. Establish a periodic rebuild/update process: one dependency family per reviewed
   change; rerun relevant native fixtures; retain failed attempts; never silently
   replace a qualified digest with a mutable tag.

No new legal conclusion or redistribution clearance is made by this audit.
The existing component notices and release inventory are inputs to that review.

## Bounded work queue and completion criteria

Reuse platform #1701 as the umbrella; issues in this fork are disabled.
The current prioritized issue checklist is in #1701. Conference preparation is
#2172; full Decoder timeout diagnosis and qualification are #2173. Neither is
a prerequisite for the main SDK/compiler release.

| Batch | Existing tracker | Concrete completion evidence |
|---|---|---|
| Conference preparation | #2172 | Refreshed walkthrough, verified offline export and project rehearsal |
| Full Decoder | #2173 | Measured timeout stage, bounded repair, independent oracle, stochastic and installed-image gates |
| Calibration drift — completed restricted model | #610 | 40 native cases passed; raw/stale/fresh counts, cleanup and chart retained in evidence/2026-09-12-readout-drift |
| Coverage/model robustness | #610 | Predeclare independent repetitions, binomial coverage uncertainty and model-mismatch cases; record failures without retuning thresholds |
| Public release packaging | #609, #640, #1585, #1839 | Clean acquisition, installed checks, exact CPU/GPU artifact smoke tests, notices and reproducibility limits |
| Bridge/TNQVM decision | #691, #1701 | Public dependency/source audit followed by one bounded build/correctness probe per path, or explicit unsupported decision |
| Decoder/Integrations expansion | #609, #640 | Named missing APIs and deterministic/reference fixtures; separate Qiskit version environments |
| Supervisor corrected-version soak | #691 | Same-host interruption/resume and exact instance/disk/group cleanup without runtime code correction |
| Hosted integration | #338, #704 | Owner-reviewed current contracts; actual admitted execution, accepted result and release receipts |

The latter two infrastructure tasks must not compete with release restoration.
Do not create a second orchestration contract. The previous platform review at
551f7c50dca3f1c2939e2c2fc5eb2949adcbc9d5 is historical and must be refreshed
before integration. No current deployment is inferred from this source audit.

## CPU/GPU evidence replay without native dependencies

Run python3 qualification/replay_offline.py from this checkout.
It invokes only named standard-library test suites in separate processes, avoiding
module-name collisions between qualification directories. It neither installs
dependencies nor starts Docker, cloud resources or services. This checks retained
evidence and boundary logic; it is not a fresh simulation or a security audit.

[Read-only bridge/TNQVM audit](accelerators/COMPATIBILITY-AUDIT.md) identifies
the exact Core compiler-discovery, library-layout, test-selection and
Fortran/OpenBLAS/MPI boundaries for the next isolated compatibility probes.
