# Local preparation binding evidence — 2026-09-09

Baseline: merged qristal `c608b155b1f4711d11c346db01b3cd7d7458800e`.
Local derivative and parent IDs are in `image.json`; these are not registry manifest
digests. Only preparation-binding code/tests are added to the qualified pipeline
image. `source-hashes.json` identifies the new files. Dependency warnings are
retained in the log with trailing whitespace trimmed.

Five unittest methods passed inside the image:

- Real qpp execution of a verified canonical byte snapshot, independent candidate
  validation and rejection of changed options after execution.
- Changed original/canonical/options/lock files, symlink and unexpected-file refusal.
- Changed digest/map/backend/settings/parser/image facts, duplicate JSON and JSON
  type substitutions refused against recomputed preparation and retained facts.
- Consistently changed original plus canonical artifacts still rejected against the
  unchanged expected manifest.
- Synthetic empty, killed-status and oversized candidate outputs rejected. Real
  process kill/deadline/overflow behavior was qualified in the prior candidate slice;
  this suite does not claim additional cancellation testing.

Runs use local Docker linux/amd64 under emulation, UID 65532, network none, no host
mounts, read-only root, 128 MiB scratch, 2 CPUs, 4 GiB including swap, 256 PIDs,
dropped capabilities and no-new-privileges. A 240-second outer command deadline
covers parsing and tests; native simulation uses a 60-second bounded capture.

The expected image policy and dependency-lock bytes are explicitly synthetic test
fixtures. This proves integrity comparisons and preparation recomputation, not that
an image/lock is registered or matches the running environment. Manifest retention,
attestation and original-to-canonical evidence require a separate trusted authority.
File fixtures are caller-owned, not a concurrent hostile shared filesystem.

No hosted material retrieval, credentials-bearing stager, runtime admission,
provider identity, result promotion, resource release or deployment topology is
implemented. No existing CLI/native dependency, platform/SDK or deployed behavior
changed. The existing full runtime suite was not repeated for this additive slice.
