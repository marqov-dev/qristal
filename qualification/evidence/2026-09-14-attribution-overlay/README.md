# Attribution overlay: actual local evidence

Based on merged PR48 (`85bc7411c9ad2b0984be602915cf857e5de80931`).
The new private image adds 140 notice files, a README and a provenance index.
`overlay-verification.json` verifies both saved archives, the exact compressed
and uncompressed ten-layer baseline, complete runtime configuration and platform,
and every file and directory in the sole added layer. No runtime files changed.
All 142 payload files have verified hashes, including the index itself.

New OCI index: `sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f`.
Archive: 514,349,056 bytes; SHA256
`451b0710cea596fcae3bf717caed723ab18677cab0e3354b11c3db9761a96ab5`.
Attribution index SHA256:
`3c806d11a02c3ada3e19fed98ac9cbca65faa97378e543af354e80a156c43a49`.

Six local amd64-emulation cases pass: QPP capabilities, identity, Bell,
asymmetric q0 bit order, unsupported Aer rejection and nonzero-noise rejection.
Each executes nonroot with no network, read-only filesystem, CPU/memory/PID
limits, and verified removal of its exact temporary container. Offline replay
passes 477 tests across 27 suites. These are local results, not native hardware
or hosted execution evidence; no new cloud resources were launched.

The first digest-addressed FROM failed because BuildKit tried resolving the
private local image name at Docker Hub. The retained gzip-compressed failure log preserves the original bytes of that
attempt. The successful build uses the existing local tag; before/after tag
observations and the build log bind it to the expected digest. Saved-archive
verification independently rejects any baseline layer or config difference.
`--network none` restricts build steps; it does not disable registry resolution.

The original attribution payload was preserved before review found that extra
unlisted source input files could be silently ignored. No unlisted bytes could
enter that payload. The assembler now rejects extras, missing files, links and
special files. A new payload binds the revised assembler; the old payload was
not overwritten. The final index distinguishes 86 bundled wheel notices,
17 installed native notices, 35 exact-source supplemental notices and two
upstream release candidates. This is incomplete coverage, not distribution
clearance. Embedded notices and OS/dependency coverage still need reconciliation.

Private retention: `Marqov Artifacts/qristal/qpp-attribution-image-2026-09-14.tar`
and `attribution-payload-v2-2026-09-14`. Git contains reviewed evidence and code,
not compiled images or the notice-text payload. Previous standalone ldd findings,
original console recovery limitation, GPU scope, native and hosted gates are
unchanged. The baseline filesystem union and attestation claims were not audited.

To reproduce preparation use `notice_overlay.py prepare PAYLOAD NEW_CONTEXT`;
the tool defaults to the index hash above. Build the prepared context locally
with BuildKit, `--platform linux/amd64 --network none`, save the image privately,
then use `notice_overlay.py verify --help` with the bound context/archive/image
identities. Verification snapshots inputs before rereading them. Run
`local_probe.py IMAGE_INDEX NEW_RECEIPT` against that exact image.
