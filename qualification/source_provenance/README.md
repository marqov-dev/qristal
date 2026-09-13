# Controlled CPU source inputs

The private CPU candidate has passed native tests after acquisition. Its packaging
receipt does not establish how inherited installed binaries were compiled. This
increment adds a **clean pre-patch source gate** and records the concrete gaps for
a fresh build. It does not retrofit provenance onto the published candidate.

## Read-only gate

```sh
python3 -B qualification/source_provenance/check.py /isolated/source/repository FULL_COMMIT_SHA --output /tmp/new-source-receipt.json
PYTHONPATH=qualification/source_provenance python3 -B -m unittest discover -s qualification/source_provenance
```

The checker accepts only a repository root at the requested full commit. It rejects
staged changes, undeclared files (including ignored outputs), changed tracked bytes
or executable modes, missing/changed submodules and symlinks escaping the source
root. It compares working bytes directly with committed blob identities, so Git's
`assume-unchanged` optimization cannot conceal edits. Submodules are checked
recursively against their parent gitlinks. SHA256 hashes and modes of accepted
files are emitted; no credentials, Git configuration contents, source text or
untracked-file contents are emitted. Output creation is exclusive.

This is deliberately **before patch application**. The existing XACC patches and
manual Decoder CMake include must subsequently be applied as named, hash-bound
transformations to a disposable copy. Existing patched workspaces should fail this
gate. Do not reset or clean them to obtain a pass. A clean result does not authenticate
the publisher, freeze a concurrently edited directory, record all dependencies,
qualify a compiler, or prove binary provenance. Run on quiescent dedicated sources;
stage/hash the effective post-patch bytes before launching compilation. Empty
untracked directories and directory permissions are not covered by this receipt.
The checker requires Python 3.9+ and a SHA-1 Git repository.

## Observed workspace audit, 13 September 2026

At qualification baseline `1c9c7aea5a9ac18cc71a7d6a985460171e9f62a5`, the
[read-only audit](workspace-audit.json) compared each existing checkout with the
current qualification source lock. It stopped at the first rejection per component:

| Component | Observation | Meaning |
| --- | --- | --- |
| XACC | Requested HEAD matches; undeclared files present | Existing experimental tree is not pristine input. The audit did not inspect those files. |
| Core | HEAD `bd3a8e28…`, requested `a5c3e5fa…` | Later research repairs exist; current HEAD cannot identify the earlier installed bytes. |
| Decoder | HEAD `a58df0cf…`, requested `13bb8f80…` | Same revision-boundary issue; do not silently promote newer code. |
| Integrations | Exact `16e4941e…`; 49 top-level entries accepted | Clean source input only; no inference about the copied installed module. |

These are expected provenance boundaries in a reused research workspace, not
new simulator failures. No source checkout, installed prefix, container or cloud
resource was changed by the audit.

## What is missing from the historical build chain

- [Source preparation](../prepare_sources.py) checks HEADs and patch applicability,
  but not the complete effective tree. A reverse-apply check does not exclude
  unrelated modifications.
- [Stage execution](../run_stage.py) mounts a reused writable workspace and writes
  command/image/status metadata without source/output hash binding. Its networked
  Core configuration can fetch dependencies. Reused compilation is explicitly
  documented in the [installed guide](../installed/README.md).
- [Python constraints](../python-constraints.txt) contain versions, not wheel/sdist
  hashes. Core and Integrations require separate Python dependency environments.
  The [historical C++ dependency lock](../evidence/2026-09-09-installed/core-dependency-lock.json)
  records additional commits absent from the top-level source lock.
- The [installed source lock](../evidence/2026-09-09-installed/source-lock.json)
  names Core `d393cf0e…`; the current source lock names `a5c3e5fa…` and the research
  checkout is newer again. Preserve all three identities; revision differences
  alone neither prove a binary mismatch nor establish equivalence.
- [Toolchain acquisition](../install-toolchain.sh) uses live apt resolution. Bind
  actual builder identity and package/compiler inventory. Durable replay requires
  retaining resolved artifacts or a suitable snapshot; byte-identical output is
  a further, separate claim.
- Manual Decoder CMake inclusion, fixture rewriting and Integrations copying in
  [installed preparation](../prepare_installed.py) need explicit transformation
  records. Current [CPU staging](../cpu_package/stage.py) correctly labels input
  bytes as having unverified build origin.

## Smallest next experiment and acceptance boundary

First reconstruct **XACC/QPP only**, since Core depends on it. Use a new disposable
workspace and the existing locked XACC/submodule revisions. Run this pre-patch
gate, bind the two reviewed XACC/CppMicroServices patches and ACZ fixture by hash,
and record the full effective source manifest. Acquire and hash all needed public
build inputs separately, including Boost and GoogleTest. Use an immutable builder
identity with recorded compiler and package versions.

The proposed native run is one isolated Linux amd64 CPU host, 2 build CPUs, 4 GiB,
256 PIDs, with an explicit 60-minute compile deadline and no workload network.
Use fresh empty build/install roots and retain commands, exit status, logs and
installed-file hashes. Run the existing phase-sensitive ACZ/QPP checks and an
installed-only consumer before claiming source-to-install success. Retain failure
logs and exact cloud cleanup evidence under the existing supervisor. If the bound
is insufficient, retain that result and revise the next protocol explicitly.
**This experiment has not run.** Do not run the historical scripts unmodified as
if they already enforce this protocol.

Then extend the same chain to Core/Decoder and separate Python/Integrations inputs,
repeat all 43 installed fixtures and the corrected negative case, assemble a new
image, and qualify its acquired digest. Required links are:

1. Pristine source receipt → exact patches → effective source/dependency manifest.
2. Source manifest + immutable builder + fresh output roots → build/log receipt.
3. Build receipt → installed byte/mode/link inventory + installed-only test receipt.
4. Install receipt → current staging/publication/acquired-image evidence chain.

The outcome will be a **new** candidate digest with stronger provenance. Keep the
current candidate available privately and its original-binary-origin limitation
intact. Public distribution review, full Decoder and hosted platform admission
remain separate work; no dependency on the current SDK/compiler release is added.

## Reconstruct pristine sources from existing Git objects

`export.py` creates a new source directory from full commit/blob objects in a local
repository and its initialized submodule repositories. It does not read modified
working files, use export-ignore rules, fetch dependencies, or change any checkout.
The submodule's recorded gitlink controls the export even if its checkout is newer.
Every written blob is checked against its Git identity; the finished tree is checked
against SHA256 hashes, modes and symlink targets, including unexpected files.
A failed export may leave a partial directory, but never a completed receipt.
Use a new destination for a retry, rather than merging into partial output.

```sh
python3 -B qualification/source_provenance/export.py /existing/xacc \
  d1edaa7ae53edc7e335f46d33160f93d6020aaa3 /new-inputs/xacc \
  --receipt /new-inputs/xacc-source.json
```

The receipt belongs outside the source directory. The supplied repositories are
local object stores, not proof of upstream publisher authenticity. This exporter
provides a way around the reused-workspace rejection without deleting research
work. Patches, fetched artifacts, builder identity and fresh installed outputs are
still separate inputs to the next build receipt. Neither this export nor a passing
source-only check promotes an existing runtime's provenance status.

The [first actual pristine-source reconstruction](../evidence/2026-09-13-pristine-sources/README.md)
exported and independently verified XACC's 9,196 files/13 submodules and
GoogleTest's 242 files. Boost and separate patch/fixture inputs are hash-bound.
This completes source reconstruction for the proposed first component; patching,
builder capture, offline compilation and installed-only tests are still pending.
