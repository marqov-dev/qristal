# Bounded sparse backend profile

Follow-up to PR27, using the same 24-qubit, four-trial Decoder fixture and 60-second process limit. One owned CPU VM uses the existing `PLAN.md` resources, observation deadline and cleanup. No shared checkout, Docker service, production image or hosted route changes.

The guest rebuilds only the previously tested MCZ/search derivative and a source-hash-bound sparse accelerator with diagnostic insertions. Removing the marked insertions recovers every original backend source byte. The fixture adds only a loaded sparse-library identity print. Cached dependencies retain their older source-lock provenance; this is not a full rebuild from the recorded repository heads.

The profile records top-level circuit phase indexes, visited/enabled nodes, visitor calls, elapsed microseconds and aggregate nanoseconds around `accept`. It emits incremental counts every 131,072 visited nodes and at phase and sampling boundaries. Gate costs are incremental per output interval; node counters are cumulative per execute call. Composite visitor calls are distinct from primitive gates. Phase indexes are positions in the actual top-level circuit, not inferred names.

For the observed single amplification iteration, Core constructs phases 0 = initial preparation, 1 = oracle, 2 = inverse preparation, 3 = zero reflection, 4 = preparation clone, then measurement instructions. This mapping comes from the pinned search source; more amplification iterations repeat phases in groups of four.

`SparseSimulator::Sample` flushes queued operations. Some gate methods also flush earlier queued work. Consequently a visitor's attributed time is not a standalone cost for that gate, and sampling time includes deferred simulation. State dumping would flush queues and alter timing; no amplitude-count probe is introduced. Timing includes instrumentation overhead and is diagnostic, not a speed benchmark.

The native run must recover a checksummed report, source/patch and loaded-library hashes, 70 QFT prerequisites, six initialization tests and exact resource cleanup. Timeout is retained as a failed caller contract, even if profiling succeeds. No production qualification or general MCZ compatibility claim follows.

```sh
python3 -B qualification/full_decoder/cloud/pack.py NEW_ARTIFACT backend-profile
python3 -B qualification/full_decoder/cloud/run.py NEW_ARTIFACT NEW_RUN_STATE
```

Final payload omits redundant command arrays; exact commands remain in the pinned guest source. Evidence and process bounds are unchanged.
