# Source-built Core packaging input gate

This read-only gate produces an inventory and next-step plan, **not a runtime**.
It does not extract files, install dependencies, build containers, publish or
contact a cloud service. Its inputs are the retained Core output archive,
executed protocol, executed `material-manifest.json`, and recovered native receipt (either the raw report or the
existing `{"result": ...}` envelope).

```
python3 -B qualification/core_package/audit.py OUTPUT.tar.gz protocol.json recovered.json material-manifest.json --output NEW-packaging-inputs.json
```

Both existing validators must accept the evidence: `core_output/output.py`
checks the archive/receipt/report and `core_native/check_result.py` checks the
native stage contract and full logs. Their current file hashes must match the
executed protocol; mismatched validator versions require a separately reviewed
compatibility decision. No duplicate archive extraction or link-validation rules
are introduced here. Missing, failed, conflicting or altered receipts fail
closed; the CLI writes no plan until validation succeeds and never overwrites an
existing plan.

The supplied material manifest is bounded to 32 MiB and its raw SHA256 must
match `protocol.materials_sha256`. Its `python/core.json` entry must bind the
checked-in wheel manifest's exact bytes/hash, and all 50 wheel entries must
match that manifest's regular-file type, size and SHA256. Missing entries,
duplicate JSON keys or wheel names, and extra wheel entries are rejected.
This connects the packaging wheel requirements to the inputs the native
execution actually verified, rather than only to the current repository state.

The resulting plan binds archive, protocol, native receipt, checker and audit
hashes; copies the already-verified retained file/mode/link inventory; lists the
50 required locked Python wheels plus retained ANTLR wheel; and records the
runtime/system ABI and notice work still needed. The wheel list is a requirement
from the checked-in acquisition manifest, not a claim that those wheel bytes
were supplied or installed by this gate. Native observations remain QPP-only.

Next work requires a new staged context that preserves the validated sibling
`install-core`/`install-xacc` layout, reconstructs the Python environment offline,
binds adapter and capability files, selects final OS dependencies, and tests the
assembled image without source/build mounts. Historical apt pins are references,
not proof of ABI compatibility with the final image. Aer, Integrations, Decoder,
public distribution, bit reproducibility and hosted admission are separate gates.

Tests use synthetic receipts and the existing native-checker fixture. They test
the preparation boundary and rejection behavior; they do not run a simulator.

When a report explicitly declares `console_artifact_binding: false`, supply
`--recovery-verification` with its separate alternate-recovery record. The audit
requires matching archive identity, verification and native classification, and
preserves the missing console binding plus the recovery-record hash in its plan.
This preserves the authenticated-object recovery distinction; it does not recreate
a lost console hash or turn local receipt hashes into publisher authentication.
Original console/retention failures and subsequent cleanup records stay separate.

Recovered envelopes require an explicit boolean binding flag and consistent source
provenance. A supplied claim of console binding is recorded as operator-reported,
with independently checked binding left unknown: this gate does not receive the
original console reference. Flipping or dropping the alternate recovery flag
cannot bypass the sidecar requirement.

## Source-built QPP staging

`stage.py` snapshots and revalidates the native archive, receipts and supplied
wheel bytes into a new context. It preserves the sibling `/work/install-core`
and `/work/install-xacc` installation paths and relative plugin links inside
`work.tar`. This avoids case-insensitive host collisions between XACC headers;
extraction is deferred to the future case-sensitive Linux image build. It copies
no build/source trees or historical virtual environment. Runtime assets reuse
the existing local adapter behind a QPP-only entry point which rejects other
backends and nonzero noise before native execution. The generated requirements
bind all 50 acquired wheels plus the retained ANTLR wheel by hash.

Staging does not install packages, build an image or run native code. Its runtime
recipe deliberately records `build_ready: false`: final OS bytes/closure and
notices must be acquired and bound before building. This is a preparation result,
not a newly qualified image. Run the eventual Python install script only in the
separately qualified linux/amd64 image build environment with local wheel inputs.

```
python3 -B qualification/core_package/stage.py OUTPUT.tar.gz protocol.json recovered-full-report.json material-manifest.json WHEEL_DIRECTORY NEW_CONTEXT --recovery-verification recovery-verification.json
```

Omit the recovery sidecar only for receipts that do not use alternate recovery.
Existing output directories are rejected. Every supplied wheel must match the
native input manifest; missing, extra or symlink wheel inputs fail closed. The
staging inventory binds the installation tar, recipe, evidence and wheel bytes;
it must be rechecked before any later build consumes the context. No compiled
artifacts or acquired wheels are committed to Git.

## Subsequent OS acquisition and local image proof

The next batch adds `os_lock.py`, `assemble.py`, `os/Dockerfile` and
`local_probe.py`. See `os/README.md` for the signed-snapshot acquisition and offline
build workflow, and `qualification/evidence/2026-09-14-os-acquisition` for its
actual successful local amd64-emulation image build and six-case probe.
The earlier staging receipt remains an unchanged input-preparation record;
subsequent build results are separate evidence. `notices.py` inventories available
wheel/native notices without claiming complete redistribution coverage.

Saved-image checks now live in `image_archive.py`; the verifier distinguishes OCI
index, amd64 manifest and config identities and verifies compressed layers plus
uncompressed diff IDs without extraction. `image_audit_guest.py` and
`wheel_linkage_guest.py` are fixed isolated-image probes, not host utilities.
Evidence is in `qualification/evidence/2026-09-14-image-audit`; it preserves three
standalone wheel-library linkage findings alongside successful installed-loader
operations. `NATIVE-IMAGE-PLAN.md` describes the next separate native-host gate.

`attribution.py` and `notice_overlay.py` now assemble pinned notice evidence and
verify a single attribution-only image layer. See `ATTRIBUTION.md` for provenance
limits and `../evidence/2026-09-14-attribution-overlay` for actual saved-archive
verification and six passing local probes. Public redistribution, native image
qualification and hosted execution remain separate gates.
