# Sparse backend profile: preparation dominates, not sampling

After PR27 merged at `3fac7a1bf9a4e5dbf41540c8355d4421296b7077`, this independent
batch rebuilt a trace-only sparse plugin alongside the previously qualified MCZ
prototype derivative. Native execution source: `8185c05` (full revisions in
`result.json`). Core remains `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`, Decoder
`a58df0cf7eff0c6002aa3fed27ae6b18fdcea036`, XACC
`d1edaa7ae53edc7e335f46d33160f93d6020aaa3`. Cached installed dependencies retain
their earlier source-lock provenance; this was not a full dependency rebuild.

The unchanged 24-qubit/four-trial caller fixture timed out at 60 seconds. It
completed one backend call, measured 100 / score 0 (string bit 1, metric bits 00), and entered another call.
No caller-result completion or full Decoder correctness is established.

## First complete backend call

| Top-level phase | Wall interval | Visitor calls | Time inside visitor calls |
|---|---:|---:|---:|
| Initial preparation | 8.468 s | 93,427 | 8.439 s |
| Oracle | 4.273 ms | 42 | 0.242 ms |
| Inverse preparation | 18.697 s | 95,272 | 18.667 s |
| Zero reflection | 0.411 ms | 40 | 0.347 ms |
| Preparation clone | 9.570 s | 93,426 | 9.533 s |
| Sampling, including final queued flush | 0.313 ms | — | — |

Total backend duration: about 36.740 seconds. The iterator visited 286,328 nodes;
282,210 were enabled and 282,207 accepted a visitor. Counts include composite
nodes, not just primitive gates. Incremental per-gate records are retained in
`backend-analysis.json`; roughly 36.639 seconds were inside `accept`, about 99.7%
of backend elapsed time. The remainder includes traversal, diagnostics, visitor
construction and bookkeeping; it is not a pure iterator measurement.

The largest accumulated visitor attributions were Tdg (12.082 s), U (6.851 s),
CPhase (6.510 s), Rz (4.982 s) and CH (3.565 s). **These are not independent gate
costs.** Public SparseSimulator queues operations and can execute earlier work
when a later gate is visited. Sampling also flushes queues. No state dump was
introduced because it would flush queues and perturb execution; active-amplitude
counts were not measured. The difference from the previous 34.573-second run
is not a controlled performance comparison or proof of instrumentation overhead.

In the second call, preparation and oracle completed; inverse preparation was
next according to the source's phase order. No later periodic checkpoint was
reached before the original timeout. The final retained profile row alone is not
a stack trace identifying the precise operation running at termination.

## Implications and next experiment

The evidence points to simulator work in the large preparation/inverse circuit,
not result retrieval or the already-bypassed MCZ construction. Public
`inverse_circuit.cpp` flattens populated controlled blocks into primitive leaves,
while the sparse visitor can handle selected controlled gates directly.
A [structure-preserving inverse experiment](../../full_decoder/cloud/INVERSE-PRESERVATION-PROTOCOL.md)
is justified, with small independent complex-state checks first. But the two
forward passes themselves take about 18 seconds: fixing the inverse alone does
not establish that the complete four-trial fixture will fit its bound. Also audit
preparation's expanded gate structure before selecting further changes. Do not
optimize Tdg in isolation based on its attributed time.

## Attempts, identity and validation

- `attempts/initial`, source `ef8865a`: only a bootstrap-exit-1 marker survived;
  exact failing stage unknown. No profile or passing stage claim.
- `attempts/bounded`, source `18e5ca5`: compact diagnostic confirmed successful
  build/prerequisite stages, fixture timeout, and an evidence envelope overflow
  of 348 encoded characters. Full profile/vectors were not retained.
- Final `8185c05`: omitted redundant command arrays, compressed more tightly and
  reduced periodic output to every 131,072 nodes. Full checksummed report recovered
  inside the same envelope. Commands remain in the pinned guest source.

The final 70 phase-sensitive QFT vectors independently replay successfully; six
initialization cases pass. Original/derived sparse source, patch, fixture, Core
prototype and loaded library hashes are bound to the retained report. Removing
all marked sparse diagnostic insertions recovers every original source byte.

All three exact instances, disks, groups and private transfer resources cleaned
automatically. No shared platform/SDK files, Docker service, production Core,
runtime source lock, public release or hosted availability changed.

Replay: `python3 -B qualification/full_decoder/cloud/analyze_backend_profile.py qualification/evidence/2026-09-12-backend-profile`.
Protocol: [BACKEND-PROFILE-PROTOCOL.md](../../full_decoder/cloud/BACKEND-PROFILE-PROTOCOL.md).
Tracking: [platform #2173](https://github.com/marqov-dev/marqov-platform/issues/2173).

## Public evidence privacy

AWS account, resource and transfer identifiers are consistently replaced with
opaque audit aliases in the public cleanup records. Equality checks still bind
the instance, disk, group and run across those records, but the public aliases
cannot query AWS. Original durable audits remain locally in the three owned run
directories. Simulator console payloads and their source/library checksums are
unchanged. Execution revision IDs above refer to the original local experiment
commits; public review history consolidates this batch to avoid publishing the
unredacted intermediate records. The exact packaged source hashes remain in each
manifest, and the final guest/instrumentation source is included in this batch.
