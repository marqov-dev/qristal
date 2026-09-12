# Maintained simulation subset and release gates

Audit baseline: Qristal main deb37d4a6dcfd05131592021c73b8c948bf37609
(merged PR18). Historical native evidence retains its original revisions.
This document defines the proposed maintenance scope, not a supported release.

## Repair, replace or retire

**CPU: replace the legacy worker image with the qualified public-source runtime.**
Retain useful QPP/Aer simulation, local noise and selected integration/decoder
capabilities. Do not restore the old poll-loop worker or SDK Python-version
bypasses. The rebuilt CPU runtime has installed-only and compiler-free image
evidence, but remains a local artifact requiring a distribution/release gate.

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
| Decoder | 9 simplified fixtures on qpp/Aer/sparse-sim; installed C++ consumer | Full algorithm: bounded historical fixture timed out; correctness and caller result contract unqualified |
| Readout mitigation | 26 native mitigation cases plus 40 native drift cases, independent calibration, signed correction | Broader drift, repeated native calibration, preparation/model mismatch |
| Standalone CUDA-Q GPU | A10G nvidia fp64/tensornet, private published candidate | Other GPU/driver combinations, scale, long-kernel termination |
| Core/CUDA-Q bridge | Source compatibility question | No native bridge proof; do not substitute standalone evidence |
| ExaTN/TNQVM | Excluded from CPU qualification | Public reconstruction and native correctness not established |
| Hosted CPU/GPU | Offline mapping and CPU VM feasibility | Platform-owned identity, admission, transport, acceptance and lifecycle |

Sources: [installed](installed/README.md), [runtime](runtime/README.md),
[methods](accelerators/README.md), [GPU publication](evidence/2026-09-11-gpu-published/README.md),
[mitigation](readout_mitigation/README.md), [conference ledger](conference/README.md).

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

| Batch | Existing tracker | Concrete completion evidence |
|---|---|---|
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
