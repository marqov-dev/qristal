# O3 compiler configuration comparison

Native source `4ca5d55` repeated the [O1 experiment](../2026-09-13-sparse-state/README.md) on a fresh owned m7i.large. The only guest code difference was BASE `-O1` → `-O3`, covered by an offline comparison test. [Protocol](../../full_decoder/cloud/O3-COMPARISON-PROTOCOL.md) was committed before execution. No fast-math, pruning, fixture, shot/algorithm or limit changes.

| Configuration | First baseline backend call | First observed backend call | Four-trial caller |
|---|---:|---:|---|
| O1, previous VM | 37.290 s | 37.526 s | Both timed out at 60 s |
| O3, this VM | 39.428 s | 39.674 s | Both timed out at 60 s |

There was no observed improvement. This is not a controlled benchmark establishing that O3 is generally slower: different VMs, fixed order, no repeated performance sample distribution, and all diagnostic consumers/Core/QFT were compiled with the same configuration. It is sufficient evidence not to claim the timeout solved by this compiler change.

The same 12 direct simulator neutrality cases passed (not 24 distinct cases across two VMs): 216 nonempty-queue checkpoints and zero final complex-state difference. The observed first call again sampled up to 24,576 stored entries and finished normal sampling with seven stored entries and empty queues. This is internal representation, not measurement outcome count. The second backend call remained incomplete. No completed caller contract or improving oracle candidate.

All compilation/provider/neutrality stages passed. Source, derivative, both stage-specific loaded sparse binaries, Core and executable identities replay against checksummed console. All temporary VM, exact disks/group and transfer resources cleaned automatically. Public infrastructure identifiers use consistent opaque aliases; original audits stay local. No QFT/init suite was rerun here, no production library/runtime/image promoted and no shared platform/SDK changes.

## Decision and next bounded work

Keep the O1/O3 comparison as negative evidence, not an optimization release. Next map the expensive preparation intervals to stable hierarchical circuit positions and count state-entry/queued-operation work at the actual flush boundaries. Avoid summing overlapping parent/child times or interpreting sparse snapshots as exclusive gate cost. This can distinguish excessive generated arithmetic/phase-estimation work from a simulator implementation bottleneck without changing pruning or algorithm semantics.

Then choose a targeted, independently checked change and rerun the unchanged caller/oracle fixture. Stochastic behavior, installed distribution and hosted execution remain separate qualification gates in [#2173](https://github.com/marqov-dev/marqov-platform/issues/2173). Existing CPU/noise, simplified Decoder and standalone GPU conference results remain valid within their earlier scope.
