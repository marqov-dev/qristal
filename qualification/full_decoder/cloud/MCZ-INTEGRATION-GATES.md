# Controlled-Z integration gates

The qualification prototype is internal research code. Native success of its
fixtures would not make it a generally usable XACC circuit or a supported release.

## Source findings that constrain a repair

Public XACC d1edaa7ae53edc7e335f46d33160f93d6020aaa3:

- `InstructionIterator.hpp` visits composite nodes before their children.
- `QppVisitor.cpp` recognizes C-U ControlModifier blocks with a single X/Y/Z base
  gate, applies the controlled matrix directly, then restores disabled blocks.
- `Circuit.hpp` enable/disable only visit children; Instruction's default
  isEnabled is true. Empty blocks need their own state (the first native negative
  gate exposed our omission). Inherited Circuit::clone would also erase the
  ControlModifier dynamic type, so an explicit clone is required.
- Generic flattening and serialization can omit empty composite contents. Direct
  metadata must not silently reach those paths or an unsupported backend.

Public Core bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a:

- `SparseStateVecAccelerator.cpp` supports direct MCZ via ControlModifier and
  restores temporary block enable state after execution.
- `InverseCircuit` clones empty C-U blocks as self-inverse. This is appropriate
  for this Z-only block, not a general inversion rule for arbitrary controlled U.
- `uniqueBitsQD` explicitly includes ControlModifier controls/base target bits.
  Generic Circuit bit-count methods do not establish equivalent behavior.

## Smallest full-fixture follow-up, only after equivalence passes

1. Keep the full Decoder fixture, source pins, runtime image and 60-second limit.
2. Build an experimental Core derivative inside one isolated CPU VM. Replace only
   the measured MCZ expansion call for the exact sparse-sim backend with the tested
   Z-only prototype. Retain the original decomposition for other backend names.
   Keep the earlier trace checkpoints and retain original/derived source and patch
   hashes, exact loaded Core identity and the prototype header identity.
3. Recheck public QFT and native initialization gates before the full fixture.
   A completed candidate must satisfy the existing independent caller oracle;
   no improvement is inconclusive. A new timeout remains a failure, even if the
   trace advances past MCZ expansion. Do not extend time or reduce trials.
4. If completion is useful, move the smallest repair into the Core fork with
   backend/IR guards and tests. Do not publish the prototype as a generic circuit
   API. Separately test serialization/flatten rejection or safe fallback, bit
   mapping and supported dispatch paths before expanding scope.
5. Characterize stochastic success and source-absent installed plugin/image
   behavior before any runtime lock, public release or hosted admission change.

Do not restore legacy orchestration, interrupt the release agent, or treat this
as an SDK/compiler release prerequisite. Platform #2173 owns these gates.
