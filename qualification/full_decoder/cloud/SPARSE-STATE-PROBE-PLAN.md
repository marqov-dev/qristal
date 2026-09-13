# Next bounded probe: preparation structure and deferred sparse state

The phase/inventory experiment at `19a853df44f7f84de87176c3a6a248997ea2f239` rules out assuming a large traversal reduction from the narrow inverse candidate. It does not yet identify the state-work cause of the roughly twofold inverse timing. This is a proposed next experiment, not executed evidence.

## Reuse the existing implementation

At Core `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`:

- `include/qristal/core/backends/sims/microsoft/sparse-sim/basic_quantum_state.hpp:32` already declares `get_wavefunction_size()`.
- `quantum_state.hpp:162` implements it as `_qubit_data.size()`. It does not dump amplitudes, call a gate, or flush queues. This measures stored entries, including any retained near-zero entries, not exact physical support after pending gates.
- `SparseSimulator.h:713`'s `dump_all` flushes `_execute_queued_ops()`; `update_state()` also flushes. Neither is a neutral observation method.
- `SparseSimulator.h:775` owns `_quantum_state`; line 778 owns `_queued_operations`. Separate pending H/Rx/Ry boolean vectors start around line 735.
- `src/backends/sims/microsoft/sparse-sim/SparseStateVecAccelerator.cpp:231` owns the simulator in the visitor. A diagnostic-only accessor can expose aggregate sizes without changing gate statements.

## Bounded implementation and acceptance

1. Derive hash-bound diagnostic copies of the sparse header/visitor. Expose stored-state size, queued permutation/phase operation count and counts of pending H/Rx/Ry flags. No amplitude values, state dump, update, seed change, pruning change or explicit flush.
2. Unit-test that taking observations leaves pending queues and subsequent complex-state results unchanged. Execute the same IR twice; include queued phase/permutation and H/rotation mixtures, not just empty queues.
3. Extend the construction inventory with stable hierarchical child paths and controlled-base vocabulary. Bound depth 128, nodes 1,000,000 and retained summaries; do not print every primitive. Attribute largest disjoint children rather than adding overlapping parent totals.
4. In the original full fixture, sample aggregate state/queue counts at phase boundaries and a fixed visitor interval. Label observed maxima as sampled maxima. Keep the 60-second consumer limit and fixture unchanged. Use the already-qualified diagnostic direct-MCZ path, binding its exact source; otherwise the earlier synthesis stall would prevent state measurement.
5. Compare with a matched uninstrumented derivative in the same toolchain. Do not infer a speedup from instrumentation timings or change thresholds to manufacture completion. Each consumer remains independently bounded; one owned VM with the existing cleanup supervisor is sufficient.
6. Select an optimization only after the state/queue and hierarchical evidence is available. Then independent phase/caller-oracle, stochastic behavior, installed-plugin and exact-image gates still apply.

Retain failed attempts and exact derivative identities. No public runtime-lock promotion, production Core change, hosted admission or shared platform/SDK edits are included. Track execution and outcomes in platform #2173 under #1701.
