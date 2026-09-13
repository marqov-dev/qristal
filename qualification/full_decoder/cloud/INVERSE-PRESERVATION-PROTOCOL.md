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
