# Native qualification of the published GPU candidate — 11 September 2026

The exact private release passed on one disposable AWS `g5.xlarge` / NVIDIA A10G.
The host imported a transferred Docker archive; it did not build the image or mount
adapter source into workloads. This closes the native-test gap for this candidate,
not the hosted Marqov admission/integration gap.

## Identity chain

| Record | Observed identity |
|---|---|
| Release source | `beecfb8fcc501c4cecefd9d12af3058ec8f1efe0` (PR17 merge) |
| Release run | [34581422039, attempt 1](https://github.com/marqov-dev/qristal/actions/runs/34581422039) |
| Registry index | `sha256:ecb6923fa1465650453de810c938eb949f809abbc1361831f0e0e14d84e95409` |
| Linux amd64 manifest / loaded host image ID | `sha256:9af6f0b834f66025a9fb031cae3d1a2774c305c11149a09d735c878b3f49295a` |
| Configuration | `sha256:e77eb03557c01a4e34cac3e7ee5fdcf005900064944d56aafd50f899cb2c3800` |
| Transferred archive, 4,803,147,965 bytes | `sha256:77b7fb176c0119c345505a979061132ddb48373feeb7afb9145b5b1867002833` |

The full registry name is `ghcr.io/marqov-dev/qristal-cudaq-gpu`. The trusted local
Docker store reported the registry index as its image ID; the AWS store reported
the platform manifest. The importer checked the complete configuration, layer
identities, non-root user, source revision, OS and architecture rather than requiring
these different digest kinds to be identical. The unchanged baked payload matches
the original release context. Supervisor source revision is retained separately in
`source-revision.txt`; it is not the image's source label.

## Native observations

| Check | Result |
|---|---|
| `nvidia`, fp64 state vector | 6 analytic circuit cases passed |
| `tensornet` | 6 analytic circuit cases passed |
| Invalid input and missing GPU | Both failed closed without candidate output |
| Requested kill, timeout, output overflow | All 3 GPU-context fault checks passed |
| Fresh recovery | `100: 16384`, exact logical-qubit-zero-first result |
| Container boundary | All 19 used the same derivative; only read-only `/inputs` mounted |

Each analytic circuit used 16,384 shots. The A10G reported driver `595.91.07` and
23,028 MiB. Baked inventory reports Python 3.12.3; CUDA-Q reports version 0.15.0,
source `f6d1f1d50d9cd4fef60011197cafe67c9035c3dc`. Small probabilistic fixtures use
the existing predeclared 0.025 per-outcome tolerance; deterministic cases require
exact counts. This is correctness/lifecycle evidence, not a scaling or speed result.

## Observer interruption and recovery

The local observer lost connectivity to the EC2 endpoint during import/execution.
Its attempted termination also failed to connect. The guest continued under its
already scheduled 55-minute shutdown bound, completed the qualification, emitted
its finish marker and was subsequently absent from EC2 instance queries. The native
result was recovered from the **same instance**, without a new launch or rerun.

Approval review rejected retaining a new full console dump because bootstrap output
could expose signed URLs. `operator/recover_filtered.py` instead retained only the
qualification chunk protocol and explicitly allowlisted status markers. The filtered
record contains 114 chunk observations. One nonfinal duplicate fragment (index 39,
139 characters) was truncated; its complete copy matched the fragment prefix and
the reconstructed payload passed its SHA-256 check. `console-recovery.json` preserves
that fact. The native result then passed independent offline verification.

Cleanup is intentionally described at the strength observed:

- The instance is absent from direct and filtered EC2 lookups.
- The task security group was deleted successfully and its absence was verified.
- Both temporary S3 objects and their private bucket were deleted; HeadBucket returned 404.
- The interrupted observer did **not persist the exact root-volume ID**. The launch
  audit also has an empty block-device map. A full-region EBS scan found no volume
  created between 10:19 and 10:23 UTC, covering the exact 10:20:53 UTC launch. This
  is the retained volume-cleanup evidence, not a fabricated per-volume-ID response.

`observer-interruption.json`, the filtered `launch-audit.json`, `cleanup.json` and
`transfer-cleanup.json` retain these distinctions. No temporary resource remains
identified by these checks. No terminated-state response or exact root-volume-ID
absence response was obtained.

Before repeating this operational pattern, persist observed instance/volume/group
IDs before each subsequent network call, retry transient observation/cleanup errors
within the original deadline, and filter console retention from the outset. Do not
infer that a working simulator supplies production resource-release authority.

## Retained evidence and replay

`release/` preserves the original six successful workflow artifact records, plus the
registry platform manifest. SPDX/provenance are losslessly compressed, with expanded
and stored hashes in its manifest. The original release record still says
`published_candidate_not_gpu_qualified`: that accurately records its publication-time
state. This later native result is separate. SLSA/source/run agreement is checked;
no independent publisher-signature verification is claimed.

`native-intent.json`, `transport-observed.json`, `source-hashes.json` and the operator
script snapshots capture the bounded procedure. The snapshots contain historical
local paths and AWS resource identifiers; they are audit evidence, not a supported
provisioning interface. Rendered bootstrap files, signed URLs, credentials, the full
console dump and the large image archive are excluded. The bucket had all four S3
public-access blocks enabled, AES256 encryption, and one-hour object GET grants.

From the repository root, without Docker, AWS access or a GPU:

```sh
python3 qualification/gpu_release/check_native.py qualification/evidence/2026-09-11-gpu-published
python3 -m unittest discover -s qualification/gpu_release -p 'test_*.py'
```

This is the public standalone CUDA-Q alternative, not a reconstructed historical
Core/CUDA-Q bridge, QB's commercial Emulator, internal vQPU, or proof of GPU memory
sanitization/long-kernel interruption. The image contains separately licensed NVIDIA
components. Candidate visibility remains private and hosted availability remains
false. Platform-owned admission, identity, material/result transport, acceptance and
lifecycle integration remain separately reviewed work.
