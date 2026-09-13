# Controlled-Z representation probe — predeclared

After merged PR26 at 257e185c8b0d65bb2b4a9ec967822fdb65223267.
Tracking: platform #2173. This is a qualification-only prototype, not a Core repair.

The previous run localized the full Decoder timeout inside 18-control Z expansion.
Existing public QPP and sparse-sim visitors support ControlModifier metadata. A
new empty C-U Circuit subclass exposes only a Z target and unique control bits,
with deep clone, enabled-state preservation and full-register permutation mapping.
It is explicitly selected only for qpp/sparse-sim; other names use the unchanged
upstream C-U decomposition. Tests flatten that fallback to primitive leaves so the
QPP/sparse visitor cannot bypass it using metadata. No upstream plugin is patched.

One independently owned CPU VM, same PLAN.md 2-vCPU/8-GiB/20-GiB infrastructure,
no inbound network or IAM profile, 1200-second observation and 300-second cleanup.
Compile limit 180 seconds; each negative/QPP/sparse process 60 seconds and 4-GiB
address-space limit. Public installed caches are reused. Each exact IR object
runs twice to check visitor disable/enable restoration. No full Decoder attempt
is included: establish representation behavior first.

Predeclared fixtures:

- QPP: six register layouts, 1–4 controls, 2–5 total qubits, including shifted
  target, spectator and reversed-control-order cases. Seven modes: direct,
  clone, inverse, pair, flattened fallback, disabled, full-register reversal.
  All 42 cases use H then Rz(0.13*(bit+1)) on every qubit, providing nonzero complex
  amplitudes at every basis index. Retain all complex vectors. Independently
  compare with the product-state formula and a sign flip exactly when target and
  all controls are 1. Pair and disabled modes leave the input state unchanged.
  Absolute amplitude and norm-error thresholds: 1e-10, without fitted global phase.
- Sparse-sim: prepare every control-bit pattern for 1–4 controls, target H,
  tested block, target H, then measure all qubits. Test direct, clone, inverse,
  pair and flattened fallback (150 cases). For 18 controls, test all-ones and
  one-zero patterns in direct/clone/inverse/pair modes (8 cases); deliberately do
  not reconstruct the known expensive 18-control fallback. All 158 fixtures
  require exactly the analytic deterministic bitstring at 64 shots, twice.
- Reject seven malformed layouts and three invalid full-register permutations.
  Check cloning preserves enabled state without aliasing it.

The installed InverseCircuit handles empty C-U clones as self-inverse. This is
appropriate for this Z-only prototype, not an assertion about arbitrary controlled
rotations. The test also exercises nested Circuit traversal and Core uniqueBitsQD.
Generic IR serialization, Circuit::flatten, generic Circuit bit-count methods,
other gates/register namespaces and dispatch to other accelerators are outside
scope. Those operations may erase empty metadata blocks and require separate
integration protections before production use.

Retain merged revisions, original source hashes, compiled binary and loaded public
runtime library hashes, all emitted records, failures and exact cleanup. Source
revisions in the manifest describe current source trees; reused installed binaries
retain their own identities and are not inferred rebuilt from those revisions.
No observation retunes tolerance, changes fixture size or extends deadlines.
Failure is evidence, not permission to claim a replacement works.

The phase tests establish the selected prototype subset only. A later full-fixture
repair still requires bounded native execution, an independent caller-result oracle,
stochastic characterization and installed-plugin/image qualification.

Pack with `python3 -B qualification/full_decoder/cloud/pack.py NEW_DIRECTORY mcz`;
run using the existing bounded cloud/run.py and a new run directory.
