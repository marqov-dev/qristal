# Stored sparse-state and queue probe

PR30 merged at `5caf589e9792acab44cc63fa3a97d814f18f0349`. Native O1 source `a37e157` ran in one independently owned m7i.large. The [protocol](../../full_decoder/cloud/STATE-PROBE-PROTOCOL.md) preserved the original 24-qubit/four-trial fixture and separate 60-second consumer limits. No production library, runtime lock, shared platform/SDK or hosted admission changed.

## Results

- Twelve direct simulator operation-sequence neutrality cases passed. At all 216 checkpoints there was pending work; 100 observations per checkpoint left snapshots unchanged. Final complex-state difference versus the no-observation route was zero. Final state collection intentionally flushes both routes equally. This is not a general XACC IR/clone test or a proof covering every state.
- Both baseline and observed four-trial fixtures timed out. Their first completed backend calls took **37,290 ms and 37,526 ms**, respectively. The 0.63% difference is descriptive, with no repetitions/randomized order or overhead confidence bound. It does not show a speedup.
- Observed phase times: initial preparation about 8.684 s, inverse about 20.018 s, preparation clone about 8.819 s. The same general preparation bottleneck persists.
- Sampled stored entries reached 20,480 during initial preparation and 24,576 during inverse/preparation clone. These are sampled lower bounds on peaks, not global maxima or exact support after pending gates. Snapshots were taken every 8,192 raw visited nodes and at phase boundaries; disabled descendants can still be visited.
- Before final sampling, 512 entries, four queued phase/permutation operations and eight pending H flags remained. The normal final flush left seven entries, with queues empty. This is transient internal structure, not a seven-outcome measurement claim.
- The second observed backend call was truncated during inverse preparation. No completed caller contract or oracle-consistent improving candidate was obtained.

The source `quantum_state.hpp:694` converts queued phase/permutation gates into operations and applies the list to every stored entry; rotations/H also reconstruct sparse maps. This supports investigating state-dependent work, but sampled snapshots do not establish exclusive per-gate cost, memory pressure, or which exact operation causes the most work. The queued list maxima are sampled too; no claim that unobserved queues stayed small.

## Reproducibility and cleanup

`result.json` is recovered from checksummed filtered console chunks. `analysis.json` and `state-observations.json` replay from that console. Source/derived header and visitor identities, both separately installed sparse plugin hashes, common Core derivative and executable hashes are bound. A final shared library path is not used to retroactively identify the baseline. Removing marked instrumentation additions restores original source bytes.

All compile/provider/neutrality stages exited zero. The two timeouts remain incomplete observations. No QFT or initialization suite was rerun in this experiment; those prior results are not counted again. All instance/disk/group/transfer resources cleaned automatically. Public infrastructure IDs are consistent opaque aliases; originals remain local.

## Next decision

Before changing algorithm semantics, the batch includes a separately predeclared compiler-only O3 repetition. The prior guest and retained build cache use O1 even under the Release name. The new configuration changes no fast-math/pruning/fixture/time bounds; it also optimizes Core and consumers, so it is a whole diagnostic configuration comparison. Its evidence is recorded separately.

If compilation flags do not resolve the bounded caller, deeper hierarchical preparation attribution remains useful. State pruning thresholds or circuit semantics must not be altered merely to fit a runtime budget. Independent caller/oracle and stochastic correctness, installed-plugin/image qualification and hosted integration remain separate gates under [#2173](https://github.com/marqov-dev/marqov-platform/issues/2173).
