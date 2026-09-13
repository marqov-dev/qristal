# CPU candidate distribution workflow

This increment prepares a manual, main-only workflow for an inventoried CPU
candidate. It corrects the inherited GPU-negative test without changing the
historical source-bound harness or reclassifying its earlier result.

## Current status

Source and offline tests are prepared. The real local archive was checksum-checked
and extracted into a derived context. No candidate was published and the new
matrix/inventory collector have not yet run natively.

The input archive remains local. Automatic approval review rejected its attempted
upload to an unpublished GitHub release because installed-binary contents and
redistribution rights were not established. The rejection happened before the
upload command ran. Do not dispatch the workflow until this specific transfer is
authorized and the exact asset is uploaded. No alternative transfer was attempted.

Requested input transfer: the existing353,060,408-byte `cpu.tar.gz`, SHA256
`de37205ac56daf601b2cf8816175656da5ed943f5c95d986c8b1886f77c729cd`, to an unpublished
`cpu-inputs-20260913` draft release in `marqov-dev/qristal`. It contains the captured
installed CPU payload and named native harness, including retained component
notices. It does not establish the original build provenance or redistribution
clearance. Do not publish the draft as a user release.

## Workflow

1. Retrieve only the named draft asset using the repository's ephemeral Actions
   token; require draft status and verify the checked-in archive SHA256.
2. Extract only the original context, verify its inventory, and bind it to the
   recorded parent context. Add the inventory collector and source/revision labels
   to a derived context. The revision describes packaging code, not the origin of
   pre-existing installed libraries.
3. Build and run the revised ten-group matrix before publication. The negative
   GPU invocation supplies a Bell circuit, requires exit2, empty stdout and the
   exact `qristal_sample_failed:backend` stderr diagnostic.
4. Publish a uniquely source/run/attempt-tagged GHCR candidate with BuildKit SPDX
   and provenance extraction. No `latest` tag or visibility change is requested.
5. Pull the exact registry digest and repeat the matrix. Export both Python
   environment inventories, resolved dpkg versions, selected notice hashes and
   baked payload hashes. Verify index→platform manifest→configuration identity,
   commands, diagnostic, packaging source and extracted provenance fields.
6. Retain records for90days in Actions and commit the selected evidence before
   expiry. The publication receipt stays `pending_acquired_checks`; a separate
   verification record reports the acquired result.

Credentials are confined to trusted acquisition and registry steps. They are not
mounted or passed to workload containers. `contents:write` supports access to the
unpublished draft; `packages:write` supports candidate publication. The job runs
only on this repository's main branch by manual dispatch, with a35minute bound.
Historical CPU/GPU evidence and available-artifact catalog remain unchanged.

Once the input transfer is authorized/completed and this workflow is merged:

```sh
gh workflow run cpu-runtime-candidate.yml --repo marqov-dev/qristal --ref main
```

## Limits

Inventories list observed metadata, not a complete license audit. Python package
names/versions and selected source/OS notice hashes do not prove every license
text was located. Preserved files and generated SPDX are separate evidence.
Extracted `.SBOM`/`.Provenance` predicates are checked for shape and source/run
consistency; raw attestation blobs/envelopes are not independently bound to their
registry subjects. Do not describe that as full cryptographic verification.

Selected apt versions still rely on live repositories. The second publication
build may differ from the first checked build; the acquired-digest test is
therefore required. Hosted admission, public redistribution, source-to-binary
provenance and byte-identical builds remain separate gates.

Research reused: GitHub documents [draft release access](https://docs.github.com/en/rest/releases/releases#list-releases)
and [binary release-asset download](https://docs.github.com/en/rest/releases/assets#get-a-release-asset).
The existing [GPU candidate workflow](../../.github/workflows/gpu-runtime-candidate.yml)
provides the pinned action versions and observed SPDX/SLSA parsing pattern.
