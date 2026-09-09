# Joined local parser / simulation / validation — 2026-09-09

Extends parser PR #7 at `4c5f94d969f6390be0d2c72eb61f8c5a0118692c`.
`image.json` records a derivative of the qualified candidate image. Only parser,
pipeline and test files are added; native libraries and existing runtime entrypoint
are unchanged. The earlier parser-only image remains in `../2026-09-09-program`.
New/overlaid source hashes are retained in `source-hashes.json`.

All three test modules passed:

- Three parser unit methods with positive and rejection cases.
- Ten real qpp/Aer parser/simulator/candidate checks (basis, directional CX, Bell).
- Four pipeline unit/integration methods: malformed options reject before parser
  or process invocation; unsupported circuits never start simulation; empty output
  fails and scratch files are removed; four real qpp/Aer roundtrips check separate
  original, canonical and exact options hashes. Comment/whitespace changes affect
  original/options identity while preserving canonical circuit and counts.

The failure-path process call is simulated in one cleanup test; real simulator
roundtrips and parser checks run against installed dependencies. This is seven
unit/integration methods plus ten standalone simulator checks, with fourteen real
simulator runs in total. Existing process-kill/overflow/deadline tests remain the
separate candidate qualification evidence; hosted cancellation is not exercised.

Runs use local Docker linux/amd64 under emulation, UID 65532, network none, no host
mounts, read-only root, 128 MiB scratch, 2 CPUs, 4 GiB including swap, 256 PIDs,
dropped capabilities and no-new-privileges. An outer 240-second command deadline
covers parsing and test execution; simulation subprocesses have a 60-second limit.
Logs retain dependency deprecation warnings with trailing whitespace trimmed.

The joined pipeline is ideal-only and X/H/CX-only. Its result is local bookkeeping,
not proof of authentic execution or original-to-canonical provenance. No hosted
schema, material delivery, attestation, provider acquisition, promotion or release
path is implemented. No platform/SDK change, native build, publication or deployment.
