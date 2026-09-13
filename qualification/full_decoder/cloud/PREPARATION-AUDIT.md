# Forward preparation: why an inverse-only fix is not enough

Source audit after merged PR28 (`66e21433a18ef0361d859614ff5bbea5e2ec448a`).
Core inspected: `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`; Decoder:
`a58df0cf7eff0c6002aa3fed27ae6b18fdcea036`; XACC:
`d1edaa7ae53edc7e335f46d33160f93d6020aaa3`.
These are source findings, not a new full-Decoder execution or deployment audit.

## What the previous native profile does and does not establish

Initial preparation made 93,427 visitor calls in 8.468 s; inverse preparation
made 95,272 in 18.697 s. The second preparation made 93,426 calls in 9.570 s.
Composite nodes are included. The inverse call-count increase is only about 2%,
so fewer metadata/decomposition nodes alone do not explain the timing gap.
Sparse-state size, queued operations and operation order remain possible causes.
No active-amplitude counts were measured. Reducing construction time or preserving
selected inverse blocks does not establish that the four-trial fixture will fit
its 60-second limit. No speedup is claimed for the new small equivalence tests.

## Source construction chain to inventory

Decoder `src/quantum_decoder.cpp:227` builds WPrime → UPrime → QPrime for each
iteration, optional repeated-symbol flags and metric adders, then appends
DecoderKernel with a clone of the preceding preparation. In
`src/decoder_kernel.cpp:303`, DecoderKernel appends SuperpositionAdder.

Core `src/circuits/superposition_adder.cpp:219` constructs MeanValueFinder and
inverts its comparison oracle. `mean_value_finder.cpp:89` and `:127` construct
CanonicalAmplitudeEstimation; the same builder also performs inverse preparation,
division, controlled AEtoMetric and inverse division. In
`canonical_amplitude_estimation.cpp:173`, the default Grover operator constructs
an inverse preparation and reflection before calling PhaseEstimation.
`phase_estimation.cpp:81` repeatedly expands controlled copies of the entire
unitary, with powers 1, 2, 4, … . These are multi-gate controlled composites, not
necessarily the single-target operations supported by the new narrow prototype.

These paths motivate an inventory; source reading alone does not assign native
cost to each child or establish that every path above contributes to this fixture.

## Backend contract learned by the inverse experiment

The selected QPP visitor (`quantum/plugins/qpp/accelerator/QppVisitor.cpp:365`)
shortcuts single controlled X/Y/Z only. H and rotations require populated
fallback decomposition. Core's sparse visitor supports X/Y/Z/H/Rx/Ry/Rz.
An empty metadata representation must therefore have explicit backend-specific
lowering or rejection. Compiling the same object against both visitors is not
compatibility evidence. The first native inverse test caught this assumption.

## Next bounded diagnostic, before a broad compiler rewrite

1. Inventory the actual prepared circuit: per named child, nested/primitive node
   counts, control count, base-gate vocabulary and eligible direct-control blocks.
   Record hashes and stop before simulation; do not report a synthesized result.
2. Compare the original and candidate inverse inventories. Keep unsupported
   composites on an explicit proven path; never silently discard their leaves.
3. If node reductions are small, measure sparse-state work with diagnostic counters
   that read existing container sizes without flushing queued operations. Bound
   aggregate output; do not use state dumping as a neutral timing probe.
4. Select one measured change, then rerun independent complex-state/phase gates
   and the original full-fixture caller-oracle experiment. Preserve all failures.

Full integration also needs the preparation's broader primitive vocabulary (U,
CNOT, phase gates, etc.), nonunitary rejection, buffer mapping, generic IR/API
constraints, stochastic validation and exact installed-image qualification.
The new helper deliberately rejects unsupported leaves instead of pretending
it can already invert the entire Decoder preparation.

## Newly exposed phase risk in the selected legacy lowering

The inverse experiment's second attempt failed controlled Rx on the selected
QPP path, with a complex-state error of 0.282897. At the inspected XACC source,
`quantum/plugins/algorithms/qpe/ControlledGateApplicator.cpp:488` expresses Rx as
U(theta,-pi/2,pi/2); `:576` lowers controlled U using a target Rz where its comment
specifies U1. Since Rz(alpha) = exp(-i alpha/2) U1(alpha), those operations differ
by a global phase in a single decomposition. Under another control, a dropped
global phase can become relative and observable. The Rx substitution predicts a
-pi/4 phase for a forward single-control expansion; its inverted primitive path
can have the opposite sign. Retained vectors must determine the actual case.

This is a source-supported explanation, not proof that every upstream revision
or installed component has the same bug. The exact installed binary remains
unmodified. The next experiment retains legacy vectors for classification while
using explicit phase-preserving candidate lowering. Do not compensate phase by
fitting the output and call the original case qualified. Controlled U/global-phase
correctness is a separate gate before broad preparation optimization or release.
