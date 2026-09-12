# Phase-sensitive QFT and retained Decoder checkpoints — predeclared

Baseline: merged Qristal 900dabfbe36d12549af2d034bfab5dadfc49d166.
Keep Core bd3a8e28, Decoder a58df0cf and public XACC d1edaa7 unchanged.
One new isolated CPU VM; use the existing account/resource binding and cleanup.
No shared Docker, platform/SDK edits or main-agent interruption.

First rebuild the diagnostic QFT provider and Core bundle as before. Run the
public QFT/IQFT services through installed QPP on every computational basis input
for n=1,2,3, with five modes: basis only, QFT, IQFT, QFT→IQFT and IQFT→QFT.
There are 70 cases. Capture complex amplitudes without measurement; do not infer
phase correctness from uniform counts or round trips alone.

Independent reference: F[y,x]=exp(+2πi*x*y/2^n)/sqrt(2^n), inverse with negative
sign. Logical q0 is the least significant bit. XACC's QppVisitor explicitly
reverses QPP operand indices to provide that convention. Basis-only cases check
it directly. Use absolute complex-amplitude error, without fitting a global
phase. Fourier tolerance 1e-6 accounts for the upstream literal π=3.1415926;
basis/round-trip tolerance and normalization error are 1e-10. Do not retune after
the observation. Preserve every complex vector for independent Python replay.

Upstream QFTTester/InverseQFTTester chiefly check expansion and print circuits;
their expected-gate comparisons are commented out. This protocol adds a
mathematical test, using the upstream QPP wave-function API shown in
QppAcceleratorTester.testExecutionInfo. No upstream algorithm source is changed.

Only if the 70 cases pass, repeat the six initialization cases and the same
24-qubit/four-trial Decoder fixture. Add service checks, monotonic checkpoints
around initialization/execution, and unbuffered stdout. The CPU capture variant
retains bounded partial output on failure. This diagnoses the previous timeout;
it does not increase its limit or create an automatic retry loop.

Limits: same m7i.large (2 vCPU/8 GiB), 20-GiB encrypted disposable disk,
4-GiB child address-space limit, 256 processes, no workload networking/credentials,
180-second builds, 30-second bundle steps, 60 seconds each for QFT tests, input
tests and the tiny fixture. Overall supervision remains 1200 seconds, cleanup
300 seconds. QFT stdout retention is 40,000 characters within the unchanged
65,536-byte capture ceiling; all other output keeps its prior bounds.

Retain a missing-service error, Fourier mismatch, failure or timeout without
another native run in this batch. Require exact resource cleanup. A QFT pass
qualifies only these small QPP state-vector fixtures, not sparse-sim, the entire
generators bundle, full Decoder, stochastic accuracy or hosted execution.
