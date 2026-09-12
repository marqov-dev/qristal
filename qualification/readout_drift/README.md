# Calibration drift: predeclared protocol

Baseline: merged PR18, deb37d4a6dcfd05131592021c73b8c948bf37609.
Reuse the measured assignment-matrix method from ../readout_mitigation;
no dependencies, image rebuild or cloud execution.

Forty native executions at 16,384 shots: five batches each containing two
calibration preparations and six separate held-out circuits, with distinct
seeds fixed in schedule(). Baseline p10/p01=.20/.10; subsequent batches
.25/.10, .35/.10, .10/.20, .05/.025. These model increased, reversed-asymmetry
and reduced error, not physical elapsed time. Use baseline calibration for
stale correction, independent current-batch calibration for refreshed
correction, and compare both against the SAME held-out counts.

Predeclared acceptance: raw probabilities within .025 of the analytic model
(exact absence for zero outcomes); fresh corrected probabilities within .08
of ideal; refreshed aggregate observable MAE at least 50% below raw in each
batch. No acceptance threshold or monotonicity requirement on stale results:
stale correction can improve or worsen estimates. No data-dependent selection.

Retain signed estimates. Approximate pointwise 95% delta-method sampling
intervals use the existing calibration-inclusive estimator. Under drift,
these quantify sampling only, not mismatch bias; coverage is NOT established.
Shared calibration/held-out samples induce correlations; do not interpret
interval overlap as a comparison significance test. The model assumes ideal
preparation and stationary-within-batch independent q0-only classical noise.
No hardware, full SPAM, correlated-readout, hosted execution or commercial
Emulator qualification.

Standard assignment matrices:
https://qiskit-community.github.io/qiskit-experiments/manuals/measurement/readout_mitigation.html
This experiment reuses our existing transparent two-outcome implementation.

Run python3 qualification/readout_drift/qualify.py --output NEW_DIRECTORY.
One existing-image container: 2 CPUs, 4 GiB, 240-second limit, non-root,
read-only, no networking; removal verified. Commit protocol before execution.
