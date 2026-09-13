# Full Decoder: timeout localized to controlled-Z expansion

12 September 2026. Predeclared source `f3fb61adc87cf1b9c9bec46451ac0c8c51b116da`,
Core `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`, Decoder
`a58df0cf7eff0c6002aa3fed27ae6b18fdcea036`, public XACC
`d1edaa7ae53edc7e335f46d33160f93d6020aaa3`. Platform tracking #2173.

One independently owned m7i.large rebuilt the Core search plugin with trace-only
insertions. The instrumenter rejects any different source hash, and removing its
marked insertions reproduces the original source exactly. The native record binds
original source, traced source, patch, rebuilt library and loaded library hashes.
Local installed prefixes and shared platform/SDK checkouts were not changed.

All 70 QFT complex-state checks and six Decoder initialization cases passed again.
These repeat existing fixtures, not 76 new distinct capability checks. The unchanged
24-qubit/four-trial full fixture still reached its 60-second bound without a result.

| Search checkpoint | Milliseconds since search execute entry | Count |
|---|---:|---:|
| Inverse expansion begins | 5 | — |
| Inverse expansion ends | 3,467 | 95,271 top-level instructions |
| Used-bit collection ends | 3,505 | 19 used qubits |
| Controlled-Z expansion begins | 3,507 | 18 controls |

No controlled-Z expansion end, amplification-clone or backend-execute checkpoint
was retained. The bounded run therefore stalls inside the MCZ expansion stage,
not inside backend simulation. This does not distinguish CPU synthesis cost,
allocation pressure or time spent in a nested operation. The clock starts at
search entry; it is not the fixture's wall-clock origin. Diagnostic overhead and
truncated output bounds preclude treating this as a general performance benchmark.

The public generator's eager Gray-code path is now a better-supported candidate
for investigation: 18 controls imply 262,144 Gray-code entries and at least
1,572,858 generated instructions before filtering by the audited source formula.
Those are source-derived operation counts, not measured allocated gates or memory.
The earlier 23-control scenario was hypothetical and is not this observed fixture.

Next: isolate small controlled-Z blocks and compare complex states against a direct
phase-flip oracle. Investigate retaining controlled-operation metadata for the
sparse-sim backend, with clone/inverse/traversal/fallback semantics explicitly
checked. Do not replace the representation in production based on this trace.
A repair needs its own predeclared bounded native run, caller-result oracle and
subsequent stochastic/installed-runtime gates. Full Decoder remains unqualified.

The original 180-second build/60-second test/1,200-second observation limits were
unchanged. Exact instance termination, root disk absence, dedicated group absence
and private transfer object/bucket cleanup completed automatically and are retained.
No replacement launch, deadline extension, shared Docker work, main-agent
interruption, runtime-lock promotion or hosted backend enablement occurred.

Replay (standard library only, no compute launch):

```sh
python3 -B qualification/full_decoder/cloud/analyze_search.py qualification/evidence/2026-09-12-search-trace
```

This rechecks the console checksum, saved complex vectors, source/library bindings,
trace timestamps and exact cleanup. Original timeout output is in result.json;
search-analysis.json is derived. All failed historical attempts remain separate.
