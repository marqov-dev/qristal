# Retained GPU release candidates

This lane prepares a retained GHCR candidate from the native-qualified adapter. It does not publish a supported release or enable hosted execution. Baseline inspected: Qristal main `ddc1b0c851ae6854a016271b19782aa12d224bdf` (PR15 merged).

## Standard mechanisms reused

- [Docker's GitHub attestation guidance](https://docs.docker.com/build/ci/github-actions/attestations/): BuildKit provenance and SPDX SBOM generation, rather than a new SBOM format or scanner. The earlier package inventory remains supporting evidence, not a substitute for the standard SBOM.
- [GHCR documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry): repository-linked container publication using the ephemeral workflow GITHUB_TOKEN. No new long-lived credential or AWS role is required. The pipeline does not change package visibility; GitHub makes newly published packages private by default.
- [GitHub manual workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow): workflow_dispatch must exist on the default branch. The publishing job additionally permits only manual execution from this repository's main branch.
- [NVIDIA's catalog](https://catalog.ngc.nvidia.com/orgs/nvidia/quantum/containers/cuda-quantum) and [cuQuantum terms](https://docs.nvidia.com/cuda/cuquantum/latest/license.html): source and runtime component licenses differ. The catalog now advertises a newer version; this lane deliberately retains the already tested 0.15.0 manifest. An upgrade is a separate qualification.

## PR checks versus publication

Pull requests run the prior offline evidence/tests, stage an exact context, build Linux amd64 and verify the baked payload under the non-root runtime user, without GPU or networking. Context hashes and observed inventory are retained as a 30-day Actions artifact. The PR check has contents-read permissions only and cannot publish. It tests packaging, not native GPU execution.

After merge, run:

```sh
gh workflow run gpu-runtime-candidate.yml --repo marqov-dev/qristal --ref main
```

The manual run repeats checks, then publishes to `ghcr.io/marqov-dev/qristal-cudaq-gpu` under a unique source/run/attempt tag. No `latest` or supported-version tag is written. Publication uses a separately built image with provenance and SPDX attestations, so the PR check's local image ID must not be treated as the published identity. Actions are pinned to inspected commit SHAs; BuildKit/scanner defaults resolve during the run, with provenance retained. Bit-for-bit rebuild reproducibility is not claimed.

The release artifact contains `release.json`, exact context hashes, build metadata, registry index, SPDX output and provenance. It is retained for 90 days in Actions; the container remains in GHCR subject to repository/package retention policy. Download and commit the release record and qualification summary before the Actions artifact expires. A digest identifies content, not a guarantee against registry deletion.

The release record explicitly says `published_candidate_not_gpu_qualified` and `hosted_available: false`. It is a build record, not a platform execution receipt, admission decision, signature-policy verification or acceptance authority. Provenance/SBOM attestations must not be described as a separately verified publisher signature.

## License treatment

The release layer adds the repository's Apache source license and a component-boundary notice, without removing any upstream files. It does not stamp Apache-2.0 over the whole container. The observed base contains CUDA-Q LICENSE/NOTICE, NVIDIA container notices, cuQuantum Python's license and OS package notices. The six-file inventory was scoped; it did not enumerate every dependency's terms.

The current cuQuantum SDK terms explicitly permit distribution subject to their conditions, including consistent downstream terms, preserving NVIDIA rights/notices and not modifying its SDK. The full image also contains other components. The generated SBOM and bundled notices support a component-by-component distribution review; scanner success is not legal clearance. Public visibility/support promotion is outside this candidate workflow. Package visibility and organization package-creation permissions must be verified after the first publication; a permission failure must not be worked around with a broad personal token.

## Native experiment: exact published digest

1. Retrieve `release.json` and inspect its source/context, registry index and attestations. Review reported components and notices.
2. Resolve the Linux amd64 image and pull by its retained registry digest on the approved qualification host. Record registry digest, resolved platform manifest and actual local Docker identity separately.
3. Verify baked payload hashes against the release context. Repeat the existing two-target matrix, invalid-input/no-GPU cases and fault/recovery checks without rebuilding or mounting source into workload containers.
4. Retain native observations and exact cleanup evidence against that published digest, then update #691/#1701 and the Marqov project. Do not inherit the earlier disposable-image qualification as if the digest were identical.

Private GHCR download authentication belongs in a trusted acquisition step, not the GPU workload. Do not place a general GitHub/AWS token in the workload VM to simplify fetching. The bounded experiment uses the trusted acquisition procedure below; this workflow supplies no hosted transport or authority.


## Trusted acquisition and archive identity

The successful PR17 release is from source `beecfb8fcc501c4cecefd9d12af3058ec8f1efe0`,
[workflow run 34581422039](https://github.com/marqov-dev/qristal/actions/runs/34581422039).
Its original six release records and the additional platform manifest are retained in
[the published-image evidence bundle](../evidence/2026-09-11-gpu-published/release).
Large SPDX/provenance documents are losslessly gzip-compressed. The manifest records
both stored and expanded byte hashes; the original publication status is preserved.
A later native observation is a separate record, not a rewrite of the build record.

Private registry authentication is performed on the trusted acquisition computer using
its normal Docker credential helper. Pull the exact registry index, select Linux amd64,
and export one tagged platform using [Docker save](https://docs.docker.com/reference/cli/docker/image/save/).
A new export may have a different archive hash; record its actual bytes rather than
assuming the retained archive hash applies to every export. The archive contains the
runtime layers; it is not retained in Git.

The experiment transfers only this archive and the bounded supervisor through two
private S3 objects. Public access is blocked; objects are encrypted, GET URLs expire
after one hour, and the temporary bucket is deleted after host cleanup. URLs and
rendered credential-bearing bootstrap files are excluded from the evidence. No general
GitHub/AWS credential or instance role is supplied to the GPU VM. Workload containers
run without networking and mount only their read-only circuit inputs.

`import_image.py` verifies the archive checksum, resolves index → Linux amd64 manifest
→ configuration digest, then checks the loaded image's full configuration, layer
identities, user, source label, architecture and OS. It does not build or modify the
runtime. Local Docker Desktop reported the index digest as its image ID; the importer
also permits the bound platform manifest or configuration digest, and rejects an
unrelated ID. [Docker's containerd image store](https://docs.docker.com/engine/storage/containerd/)
supports image indices and attestations that the classic store cannot represent.
The registry index, platform manifest, configuration and local Docker ID are recorded
separately instead of assuming all four identifiers are interchangeable.

After privately retrieving the archive and three small release/index/platform files on
the approved disposable host:

```sh
python3 qualification/gpu_release/import_image.py \
  --archive /path/to/candidate.tar.gz \
  --archive-sha256 sha256:ACTUAL_ACQUISITION_CHECKSUM \
  --bundle /path/to/release-records --output /path/to/build.json
python3 qualification/gpu_package/qualify.py \
  --build /path/to/build.json --output /path/to/new-native-output
```

This remains an operator-controlled experiment. File hashes and presigned downloads
are not platform admission, publisher authentication or an accepted-result receipt.


The local archive is about 4.8 GB. This first transfer was limited by the acquisition
computer's uplink, while no GPU host was allocated. Future repeated qualification
should place trusted acquisition near the temporary host or use an explicitly scoped
registry delivery mechanism. That is a transport optimization to review with the
platform owner, not a reason to put broad credentials in workload containers.


The [published-digest A10G experiment](../evidence/2026-09-11-gpu-published) passed
12 circuits, two negatives, three context faults and fresh recovery. Its local
observer lost AWS connectivity, so the same host’s checksummed result was recovered
through an allowlisted console filter. Instance/group/bucket absence and a regional
launch-window volume scan were verified; the exact root-volume ID was not retained.
See the evidence record for that limitation and bounded observer-hardening follow-up.
