# Published CPU candidate — acquired native checks passed

The first CPU distribution run completed successfully at source
`bb1ccc1601ce6962101cfa87f2c44d4f7ffebc91`:
[run34743836599, attempt1](https://github.com/marqov-dev/qristal/actions/runs/34743836599).

Registry index:
`ghcr.io/marqov-dev/qristal-cpu@sha256:c500987ef91ab0e0d3dd32ea75436785308ae1603c221762291d9c13dff431c5`

Configuration:
`sha256:343e330ac7d2b40e81542c13c18753a233661f82c923b03ff772271e3d903402`

The package API independently reported **private** visibility. Authenticated
maintainers can acquire this candidate; no public visibility change or hosted
Marqov admission occurred. The installed-input archive was uploaded only after
specific user approval and remains an unpublished draft asset. Its server-reported
SHA256 matches the committed input identity.

## What ran

The workflow retrieved and checked the original archive/context, derived a
context with inventory collection and packaging labels, built and tested a local
candidate, published a uniquely tagged candidate, then pulled the exact registry
index and tested its configuration. Both passes ran the same ten groups, including
43 functional fixtures (8Core,10noise,16Integrations,9simplifiedDecoder). These are
repeated checks of43 fixtures, not86 different tests. Runtime containers had no
host mounts or network, used a non-root UID, read-only root and bounded CPU,
memory and PID settings. No workload source overlay was used.

The corrected GPU-negative case supplies a valid Bell program and verifies exit2,
empty stdout and exactly `qristal_sample_failed:backend` on stderr. It now proves
unsupported-backend rejection; the earlier missing-program result remains
unchanged in its historical evidence.

## Inventory and retained evidence

- Python3.10.12, x86_64;49 Core-environment and12 integration-environment package entries.
-130 resolved dpkg package entries;214 selected notice-file hashes.
- SPDX2.3 with219 package entries; extracted SLSA provenance with matching source/run fields.

These counts describe different inventory scopes and should not be added together.
The SPDX JSON is retained as lossless gzip. `records.json` binds compressed bytes,
original bytes and lengths; all other reports and full matrix logs are retained
without compression. The original publication receipt still says acquisition
checks pending; the separate `verification.json` records subsequent success.

```sh
python3 -B qualification/cpu_release/retained.py qualification/evidence/2026-09-13-cpu-published
python3 -B qualification/distribution/check.py
```

Independent local replay passed after artifact download. The retained verifier
checks workflow result, draft input identity, observed visibility, registry index
→ platform manifest → configuration identity, exact workload commands, corrected
negative diagnostic, inventory payload hashes and source/run consistency. No
additional AWS instance or shared Docker process was launched for this run;
GitHub hosted runners performed the work. The candidate and draft input asset are
intentional retained artifacts, not temporary cloud VMs awaiting cleanup.

## Limits and next work

The packaging revision does not establish the original build provenance of the
reused installed binaries. Apt is not snapshot-pinned. The notice scan and SPDX
record are not redistribution clearance. Extracted provenance predicates are
checked for consistency; raw attestation envelopes/subjects are not independently
verified cryptographically. Current matrix/inventory source hashes are enforced;
future changes must preserve historical verification contracts or source snapshots.

Remaining: controlled source-to-binary receipts, component redistribution review,
public access decision, and broader runtime qualification. Full Decoder, original
Core GPU bridge, TNQVM, commercial Emulator, internal vQPU and hosted integration
remain outside this result. Existing conference science charts are unchanged.
