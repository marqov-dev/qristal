# First retained GPU candidate: publication succeeded, evidence job failed

Run [34569705163](https://github.com/marqov-dev/qristal/actions/runs/34569705163)
used merged source `561a02b49d377af9e4adf5b8b0f05bbb99659f7e`. Its check job
passed 31 tests, saved evidence replay, an actual amd64 build and non-root,
no-network/no-GPU baked inventory verification. Its publication step succeeded.
The subsequent record validation and artifact upload steps failed; the overall
workflow therefore failed. This is not a successful release workflow run.

Published private candidate:

`ghcr.io/marqov-dev/qristal-cudaq-gpu@sha256:1b51260a1e7cdc3f4fbc675d94fb0ca07867dc730bfcb5a3b9b25245e82560ef`

The raw index hashes to that digest. Its Linux amd64 manifest is
`sha256:35dbf1ead7b6c9cca0900a93e74da560db9d116c48917b449d5bfae249f8ba4a`,
whose raw bytes also match. Its image configuration digest is
`sha256:9c3e6d3d51c5fc4cd04766257cc7194e65ddf458f47d3bf7beb8ffc15676031b`.
These are distinct identities, not interchangeable with the earlier local build.

## Findings and recovery

The retained image actually has **SLSA v1** provenance: `buildType` lives under
`buildDefinition`. Our original checker expected SLSA v0.2's top-level field.
The SPDX 2.3 extraction succeeded and contains 418 package entries. The fallback
artifact upload used `.release/*.json`, which was skipped by the action's default
hidden-file exclusion. The check artifact used explicit file paths and survived.

The original release JSON and metadata artifact were not retained. We recovered
the raw registry index, platform manifest and extracted attestations through
the existing Docker credential setup. `reconstructed-release.json` is explicitly
a local reconstruction from the successful check context, published digest and
workflow identity, **not** the lost original file. `recovery.json` records origins
and exact file hashes. The large SPDX/provenance JSON files are losslessly gzip-compressed; both compressed and expanded hashes are recorded. The context was independently reproduced from merged source.

The fix accepts the documented BuildKit v1 and legacy v0.2 layouts, rejects absent
or unknown documents, and explicitly lists the six intended JSON files for upload.
It does not broaden uploads to arbitrary hidden files. These extracted-document
checks are not independent publisher signature verification, legal clearance or
platform admission. Attestations and scan results do not prove native GPU execution.

Research reused:

- [Docker SLSA definitions](https://docs.docker.com/build/metadata/attestations/slsa-definitions/)
- [BuildKit provenance](https://github.com/moby/buildkit/blob/master/docs/attestations/slsa-provenance.md)
- [Upload-artifact hidden-file behavior](https://github.com/actions/upload-artifact/blob/main/README.md#uploading-hidden-files)
- [Docker save/load transport](https://docs.docker.com/reference/cli/docker/image/save/)

Next: qualify this exact published image using a credential-free GPU workload,
retain transport/configuration identity and cleanup observations, and verify the
corrected publication workflow after merge. The registry remains private; an
anonymous scoped registry read returned HTTP 401. Hosted availability remains false.
