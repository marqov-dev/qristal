# Attribution evidence for the source-built QPP runtime

`attribution.py` assembles a private payload from three independently pinned
inventories: the staged runtime inputs, notices recovered from exact source
inputs, and upstream release license candidates. It retains these provenance
categories rather than treating upstream text as proof of the acquired wheel's
contents. The payload contains 140 notice files, a README and a machine-readable
index with individual file hashes. The index itself must be pinned separately.

The named-notice collection is deliberately incomplete. Before public compiled
artifact distribution, reconcile embedded notices (including PLY), OS package
copyright documentation, source dependency obligations and the exact wheel
contents. The ANTLR and OpenPulse upstream candidates need an explicit coverage
decision. Neither file presence nor an Apache-licensed top-level project clears
all bundled dependencies. No public image release is authorized by this report.

The next image uses one COPY layer for `/opt/qristal/attribution/`. Verification
must establish full runtime configuration equality, the original platform and
all original diff IDs followed by exactly one layer. Inspect that layer's bytes:
matching image ancestry alone cannot rule out a changed runtime file or whiteout.
BuildKit may require a local tag to resolve the retained image. That tag is only
a resolution aid: bind its observed identity and reject any resulting archive
whose complete base layer chain or runtime configuration differs from the pinned
base. Build networking disabled does not prevent registry metadata resolution.
Check every payload file, including the README and index, against the independently
pinned payload. Local probes must target the new immutable image identity.

Keep original image and native-source evidence unchanged. Attribution layering
creates a new image; it cannot inherit the original archive hash or become a
native-image/hosted qualification merely by preserving its runtime files.

## Remaining release work

1. Reconcile complete distribution coverage, publishable provenance/SBOM and
   supported compatibility scope. Keep acquired binary artifacts private until
   the distribution decision is recorded.
2. Freeze and run the separately authorized bounded native amd64 image protocol;
   retain archive identities, result checks and exact-resource cleanup evidence.
3. Obtain managed-execution owner admission for the exact image/profile, then
   demonstrate submission, isolated execution, accepted results and lifecycle
   receipts. Do not restore legacy polling workers or alter the main agent's
   infrastructure from this lane.

Track these under platform #1701, packaging #609/#640/#1585/#1839 and hosted
#338/#704. Full Decoder (#2173) does not block this work. Existing standalone
CUDA-Q evidence does not qualify the old Core GPU bridge or every simulator.
