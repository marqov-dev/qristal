# Experimental Decoder derivative: MCZ stall bypassed, backend now measured

Native protocol/source de145b7 (exact full revision retained in result.json), after
merged PR26 at 257e185c8b0d65bb2b4a9ec967822fdb65223267. The Core derivative uses
the source-bound header that passed 42 complex-state, 158 sparse-interference and
10 rejection checks. Only the sparse-sim MCZ representation changes; all original
fixture, trial, threshold, backend and process limits remain fixed.

All 70 QFT and six native initialization cases passed again. The full 24-qubit,
four-trial fixture still timed out at 60 seconds and did not return a caller result.
It now advances beyond the previous controlled-Z expansion stall:

| Checkpoint | First search iteration (ms after search entry) | Second iteration |
|---|---:|---:|
| Inverse expansion ends | 3,406 | 41,387 |
| MCZ expansion begins / ends | 3,426 / 3,426 | 41,407 / 41,407 |
| Amplification cloning ends | 3,429 | 41,410 |
| Backend execute begins | 3,430 | 41,411 |
| Backend execute ends | 38,003 | Not observed before timeout |

The first backend call took 34,573 ms including its traversal/simulator work and
returned raw measurement 000, score 0, string 0. This is a non-improving intermediate
sample, not the caller-result contract, an oracle-consistent improving answer or
full algorithm correctness. The second backend call began before the original
timeout. Do not extend the bound or reduce trials to relabel this fixture a pass.

MCZ construction completing at the same millisecond timestamp means below this
clock's resolution, not zero cost or a general speedup claim. Its reported zero
child instructions means an empty metadata block; the controlled operation still
executes. Top-level backend circuit count 8 conceals nested instructions, including
95,271 inverse-preparation instructions. It is not an eight-gate circuit.

This supports retaining the direct-Z approach as a bounded repair candidate.
The new measured slow stage is backend execution, not MCZ expansion. Next: profile
traversal/clone/primitive-operation counts and sparse-state work, separating state
preparation, oracle, inverse preparation and reflection. Preserve complex-state
and caller-oracle gates. No additional native profile is claimed here.

The experimental Core was rebuilt and loaded with matching recorded path/hash;
original/derived source, patch and qualified header identities are retained.
One dedicated VM, exact root disk, security group and transfer object/bucket all
cleaned automatically within their original limits. No shared Docker, platform/SDK
edits, main-agent interruption, installed runtime promotion or hosted enablement.

Replay (one shell line): `python3 -B qualification/full_decoder/cloud/analyze_mcz_decoder.py
qualification/evidence/2026-09-12-mcz-decoder`. QFT vectors and cleanup are checked
alongside source/library bindings and the partial search trace. Full Decoder remains
unqualified and the experimental helper is not a supported generic circuit API.
