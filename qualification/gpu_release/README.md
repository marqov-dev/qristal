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

## Next native experiment: exact published digest

1. Retrieve `release.json` and inspect its source/context, registry index and attestations. Review reported components and notices.
2. Resolve the Linux amd64 image and pull by its retained registry digest on the approved qualification host. Record registry digest, resolved platform manifest and actual local Docker identity separately.
3. Verify baked payload hashes against the release context. Repeat the existing two-target matrix, invalid-input/no-GPU cases and fault/recovery checks without rebuilding or mounting source into workload containers.
4. Retain native observations and exact cleanup evidence against that published digest, then update #691/#1701 and the Marqov project. Do not inherit the earlier disposable-image qualification as if the digest were identical.

Private GHCR download authentication belongs in a trusted acquisition step, not the GPU workload. Do not place a general GitHub/AWS token in the workload VM to simplify fetching. A credential-minimal acquisition/transport design is still required before the native published-artifact test; this workflow supplies no hosted transport or authority.
