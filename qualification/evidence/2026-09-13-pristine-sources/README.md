# Pristine public build-source reconstruction — 13 September 2026

Locked Git objects were exported into new local directories, without resetting or
copying the modified research working trees. XACC commit
`d1edaa7ae53edc7e335f46d33160f93d6020aaa3` produced **9,196 files, 382,070,115 bytes,
and 13 recursive submodules**. GoogleTest commit
`58d77fa8070e8cec2dc1ed015d66b454c8d78850` produced **242 files and 3,944,990 bytes**.
Counts include vendored source/test data and symlink target bytes; they are not
runtime package counts or claims about which files compilation will use.

Both complete exported trees were independently rechecked in a fresh Python
process against the retained receipts. The Boost 1.75.0 archive matched the
existing source-lock SHA256. The two declared compatibility patches, ACZ fixture,
source lock and toolchain recipe were copied as separate inputs, with hashes in
[summary.json](summary.json). Patches have **not** been applied and no compiler,
container, cloud resource or dependency installation was started in this step.

The full per-file source receipts are retained as deterministic gzip files.
`summary.json` binds both stored and decompressed SHA256 values and the checker/
exporter source hashes. These hashes establish consistency, not upstream publisher
authentication. Export used locally available public Git object databases, not
fresh network acquisition. No private QB dependency was needed for this export.

The prepared local input root is `/private/tmp/qb-pristine-source-20260913`.
It is disposable and not itself a released download. If lost, reproduce the export
from the pinned objects using the [source tools](../../source_provenance/README.md).
The retained manifests contain paths, identities, modes and hashes rather than the
source code or a binary archive.

Next: apply the named patches in a separate disposable source copy, bind the
effective tree and immutable builder, compile into empty build/install roots,
then run phase-sensitive QPP and installed-only tests. This result establishes
source availability and exact source reconstruction, **not source-to-binary
provenance or a new qualified runtime**. The existing private CPU candidate's
original-binary-origin limitation remains unchanged.
