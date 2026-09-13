# Next candidate: preserve supported controlled operations during inversion

This is a proposed bounded experiment, not an implemented repair or qualification.
Proceed only if the backend profile supports inverse preparation as a material cost.

## Public-source basis

At Core `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`,
`src/circuits/inverse_circuit.cpp` traverses every enabled primitive leaf, clones
those leaves, reverses them and inverts their gate parameters. A populated C-U
block therefore loses its controlled-operation metadata. Empty C-U blocks are
cloned and later treated as self-inverse; that is valid for the qualified direct
Z prototype, not arbitrary controlled rotations.

The sparse visitor, in `src/backends/sims/microsoft/sparse-sim/SparseStateVecAccelerator.cpp`,
already supports direct controlled X/Y/Z/H/Rx/Ry/Rz through ControlModifier.
The full fixture's inverse contains 95,271 instructions. These facts motivate a
structure-preserving inverse candidate; they do not prove it is faster or correct.

## Smallest equivalence gate before a full-fixture run

1. Implement a qualification-only inverse helper for an explicit subset of
   controlled X/Y/Z/H and numeric Rx/Ry/Rz blocks. Reverse composite order;
   negate rotation angles; preserve controls, target, buffer names and independent
   enabled state. Never assume all empty controlled blocks are self-inverse.
2. Reject unsupported/nonunitary gates and malformed metadata explicitly. Keep
   the existing primitive-decomposition path available for supported fallbacks.
   Do not silently drop unknown gates or rewrite the generic public inverse API.
3. On small registers, compare full complex amplitudes against independent
   controlled matrices and the forced primitive inverse. Include nonzero complex
   preparation amplitudes, both rotation signs, mixed nested gates, repeated use
   of the same IR, clone/disable and forward/inverse round trips. Do not fit away
   global phase: a phase becomes observable under control.
4. Include sparse interference checks and at least one bit mapping that changes
   the active bit set. Preserve all failing observations; no tolerance retuning.
5. Only after equivalence passes, use the unchanged 24-qubit/four-trial fixture
   and 60-second bound in a new source/patch-bound VM experiment. Record actual
   instruction counts and loaded plugin identity. A no-improvement observation
   is not a successful decoded result.

Even a faster completed caller result is followed by independent caller-oracle,
stochastic-success, installed-plugin and exact distributable-image gates. This
work remains independent of platform admission, SDK/compiler and hosted release.

## First native equivalence experiment (after PR28)

`structured_inverse.hpp` is a qualification-only helper for seven explicitly
supported single-target gate names. It validates q-register controls, uses fresh
base instructions and preserves controlled metadata while reversing nested order.
It rejects unsupported leaf gates, opaque empty composites and malformed input.
It does not implement the full preparation gate vocabulary (U, CPhase, CH, etc.).

Predeclared inventory: 160 QPP complex-state cases = two layouts × ten operations
(X/Y/Z/H and signed Rx/Ry/Rz) × eight modes. Every exact IR runs twice. Modes:
direct inverse, populated upstream C-U inverse, roundtrip, clone, disabled clone,
active-set-changing mapping, forced primitive inverse and nested inverse. Native
independent dense matrices require max absolute complex error <1e-10 without
phase fitting. Retain vectors for the 40 direct/primitive inverse cases for
independent Python replay; other cases retain native errors and source-bound
matrix assertions. Twenty sparse roundtrips each run twice with exactly 64 zero
counts required. Twelve malformed-input cases must reject.

One existing bounded CPU VM protocol; compile ≤180 s, each test mode ≤60 s,
unchanged observation/cleanup limits. Only the standalone consumer is compiled;
installed simulator libraries are reused and their loaded hashes recorded. This
experiment does not execute the full Decoder or qualify the installed image.

The first attempt compiled and passed 12 input rejections, but QPP failed the
first nested controlled-Ry case (error 0.0428301). Source inspection confirmed
this selected QPP visitor only shortcuts controlled X/Y/Z; empty H/Rx/Ry/Rz
metadata is skipped. The prototype had assumed the broader sparse visitor subset
also applied to QPP. This attempt and cleanup remain retained.

The next separately declared run explicitly lowers H/rotation metadata to the
existing decomposition for QPP; sparse-sim receives direct metadata. The same
160-case complex-state inventory and 1e-10 bound remain. Add 20 inverse-only sparse
interference cases: complex product preparation, controlled inverse, H on target,
16,384 shots, every outcome within 0.025 absolute probability of the independent
dense model. This prevents a pair of omitted forward/inverse operations from
passing only roundtrip checks. No fixed seed is claimed for this sparse backend.
These sampling cases are separate from the existing 20 exact 64-shot roundtrips.
