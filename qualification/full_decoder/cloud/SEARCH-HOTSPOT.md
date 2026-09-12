# Next search diagnostic — source-supported hypothesis, not a measured profile

The retained native trace reaches exponential-search iteration 1. It does not
show a measurement or completed Decoder execution before the 60-second timeout.
That narrows the search, but does not locate the timeout within the iteration.

Core bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a,
`src/algorithms/exponential_search/exponential_search.cpp:188–283`:
after the iteration marker, it expands the inverse state preparation, gathers
used qubits, expands a many-controlled Z reflection, clones amplification
circuits, adds measurements, and finally calls the backend. Any of these stages
could account for the retained timeout.

There is a concrete compilation-cost hypothesis worth testing first:

- The reflection sends a one-gate Z circuit and all-but-one used qubits to C-U.
- Public XACC d1edaa7ae53edc7e335f46d33160f93d6020aaa3,
  `quantum/plugins/algorithms/qpe/ControlledGateApplicator.cpp:313–353`, eagerly
  selects Gray-code synthesis for this form with more than two controls.
- `_generate_gray_code` materializes 2^k entries for k controls. Each nonzero
  entry invokes `_apply_cu`, which appends six instructions before additional
  control operations or later removal. The final zero-rotation filter performs
  a linear `std::find` through the recorded removal indices for each instruction.

| Hypothetical controls k | Gray-code entries | Six-instruction calls before filtering |
|---|---:|---:|
| 4 | 16 | 90 |
| 8 | 256 | 1,530 |
| 16 | 65,536 | 393,210 |
| 23 | 8,388,608 | 50,331,642 |

These are source-derived counts, **not measured gate counts for this fixture**.
The trace does not yet report how many of its 24 qubits the reflection uses.
Do not infer a speedup, required memory or exact root cause from this table.

Core's `SparseStateVecAccelerator.cpp:116–201` and XACC's
`QppVisitor.cpp:365–433` can execute suitable C-U blocks through their controlled
operation metadata; sparse-sim directly handles MCZ. This suggests a possible
future backend-specific representation that avoids eagerly expanding a huge
decomposition. It is not a validated repair: clone/inverse behavior, traversal,
fallback semantics and phase correctness must be preserved.

Smallest next experiment: add flushed monotonic checkpoints and control/gate
counts immediately around inverse expansion, unique-bit collection, MCZ
expansion, cloning and backend execution. Apply trace-only source changes in the
isolated guest, retain their patch/hash and rebuild the Core plugin. Keep the
same fixture and 60-second bound; no algorithm, backend, threshold or time-limit
change. Only after the hot stage is observed should a separate bounded repair
and small phase-sensitive equivalence test be selected. No additional native
run was performed for this source audit.
