# Compiler optimization comparison — fixed follow-up

The a37e157 O1 state probe passed 12 neutrality cases and both complete first backend calls, but neither four-trial caller completed within 60 seconds. Stored states reached 24,576 at observed checkpoints. The locally retained original build cache also declares Release flags `-O1 -DNDEBUG`; the word Release alone does not establish O3.

Before changing simulator or algorithm semantics, repeat the same paired baseline/observed experiment at O3. The only guest-source difference is `-O1` → `-O3` in BASE. No fast-math, pruning threshold, fixture, sampling interval or time/memory/output limit changes. Core, QFT and consumer compilation also use this flag, so this tests the entire diagnostic build configuration, not exclusive attribution to sparse-simulator optimization. A fresh owned VM uses the same m7i.large type and toolchain. Cross-VM/run order and stochastic effects prevent a controlled benchmark claim.

Keep the 12-case native observation-neutrality gate. Retain failures including compiler timeout. A completed caller must still satisfy its unchanged result contract; no-improvement is inconclusive. Even an oracle-consistent candidate does not qualify stochastic reliability, installed distribution or hosted use. Both per-consumer 60-second limits and existing cleanup supervision remain unchanged.
