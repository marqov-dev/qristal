# Restricted program parser evidence — 2026-09-09

Fork baseline: merged qristal `1b68475c4afb811f528cf782a4e832198f67bea2`.
`image.json` records the final local derivative and qualified candidate-image parent;
these are image/config IDs, not published registry manifest digests. The overlay
adds only program_guard.py and its tests. Native runtime and existing CLI unchanged.
New source hashes are in `source-hashes.json`.

- Three parser test methods pass with positive normalization/idempotence/register
  cases and negative circuit semantics, gate/profile, include and bound cases.
- Ten real simulator checks pass: qpp and Aer each run X(q0), X(q1), forward CX,
  reverse CX and Bell on canonicalized source, followed by independent count/hash
  validation. Directional CX tests check control/target preservation.
- The installed Qiskit 0.46 parser source was inspected for loads(strict=True,
  include_path=()) behavior. Expected dependency deprecation warnings are retained
  in the unit log; they are not missing dependencies or test failures.

Tests run inside local Docker linux/amd64 under emulation, non-root, network none,
no host mounts, read-only root, 128 MiB scratch, 2 CPUs, 4 GiB memory including swap,
256 PIDs, dropped capabilities and no-new-privileges. The outer command deadline
is 240 seconds; native workload calls use a 60-second bounded process capture.
Parsing test programs remain inside that container boundary.

This is a narrow X/H/CX ideal-sampling parser profile, not qualification of all
OpenQASM 2, all qelib gates or general circuit equivalence. One complete final
measurement block is required; equivalent ordered scalar measurements are accepted.
The parser runs before the operation-count check and must remain isolated even
for rejected input. Its output is fresh canonical source with a distinct hash;
original-to-canonical provenance must be bound by a future trusted integration.

No hosted schema, admission, attestation, artifact promotion, resource-release or
cancellation behavior is established. No native dependency rebuild, registry push,
platform/SDK change, deployment or paid job was performed. Prior full runtime
regressions were not repeated because the existing runtime/CLI is unchanged.
