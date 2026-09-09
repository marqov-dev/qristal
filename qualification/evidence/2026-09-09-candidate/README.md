# Independent local candidate validation — 2026-09-09

Source baseline: merged qristal `5b40d7ff063fa868c2f5b32d241e7f4f977b21c4`.
The new files' SHA-256 values are recorded in `source-hashes.json`. `image.json`
records the qualified parent and local derivative image IDs. Neither is a published
registry manifest digest. No native runtime files, entrypoint or dependency were
changed by the derivative: it adds the validator and qualification helpers/tests.

Validation:

- `test_candidate.py.log`: five unit test methods with malformed/changed-field
  cases, duplicate keys at both object levels, invalid encoding/constants, trailing
  content, wrong expected facts, signal/nonzero exits and all 4096 twelve-bit outcomes.
- `test_bounded_process.py.log`: four unit test methods for stdout/stderr capture,
  stream overflow, deadlines (including closed pipes and an exited parent with a
  descendant retaining pipes), and SIGKILL status. These are local process tests.
- `test_candidate_image.py.log`: 29 checks. Six real simulator runs (qpp/Aer ×
  X(q0), X(q1), Bell) are independently validated. Eighteen changed expected-fact
  cases are rejected. Five failure cases cover zero exit without output, SIGKILL,
  stdout overflow, stderr overflow and deadline. Options/program files are staged
  by fixed test code inside the container, not retrieved through a hosted gateway.

All three test modules passed inside local linux/amd64 Docker under emulation,
UID 65532, network none, no host mounts, read-only root, 128 MiB scratch, 2 CPUs,
4 GiB memory including swap, 256 PIDs, dropped capabilities and no-new-privileges.
The image runner imposes a 240-second command deadline and removes the named
container on exit. Inner native commands have a 60-second deadline. Overflow
capture retains at most the configured stream limit plus one byte before failing.

`LocalCounts` is content-checked local data, not proof of execution, authenticated
provider provenance or a hosted receipt. Program syntax/measurement restrictions
are not established by JSON validation. Positional labels q[0], q[1], etc. describe
the local qubit convention, not a verified arbitrary classical-register mapping.
Seed/options/runtime bindings must be established separately by trusted provenance.
No noise, GPU or commercial-plugin expansion is claimed by this ideal-only harness.

The previous 43 CPU fixture suite was not rerun because native code and the runtime
adapter are unchanged. This milestone tests the new candidate boundary using the
existing qualified image. No platform/SDK modification, publication, deployment,
paid job or hosted cancellation test occurred.
