# Native stale and refreshed calibration

The predeclared40-case experiment passed on the existing immutable Qristal/Aer
CPU image. Executed source:52b376d6d64d1c6b9a0b43cb2711ecf718231fbc.
The protocol originated in b6b34a6 and was merged before this run.
No thresholds, cases or native source were changed during execution.

| Measurement p10/p01 | Raw MAE | Stale MAE | Fresh MAE |
|---|---:|---:|---:|
| .20/.10 | .25018 | .01032 | .01032 |
| .25/.10 | .29913 | .06877 | .01409 |
| .35/.10 | .40058 | .21224 | .00857 |
| .10/.20 | .24692 | .27010 | .00661 |
| .05/.025 | .06145 | .27359 | .00307 |

Mean absolute error averages Z0/Z0Z1 across six held-out circuits. Each setting
has separate prepared-zero/one calibration samples. Each of40 executions uses
16384shots and a distinct fixed seed. Stale correction reuses baseline calibration;
fresh correction uses the current setting's calibration on the same held-out data.
Baseline stale/fresh are intentionally identical.

All raw analytic and fresh-probability checks passed, with fresh MAE at least50%
below raw in every setting (observed reduction approximately95.0–97.9%).
No improvement threshold was imposed on stale correction. Stale correction was
worse than raw for reversed asymmetry and improved noise; in the latter case,
its MAE was4.45times raw. These are descriptive fixture results.

One non-root, read-only, network-disabled container ran with2CPUs/4GiB and the
original240-second deadline. It used a source overlay on the existing pinned
image; no image build, dependency install or AWS launch. Recorded container
absence was verified. Other containers were not changed.

Counts, exact programs/options, source hashes, stdout and cleanup are retained.
The checker also binds the reused mitigation estimator. Four new replay/mutation
tests reject changed summaries, mismatched cleanup and altered native-output copies.

This is a stationary-within-batch independent q0 readout model with ideal
preparation, not physical drift over time, full SPAM or hosted execution.
Sampling intervals exclude systematic mismatch bias and signed estimates are
not clipped. This native experiment complements the separate synthetic coverage
study; it does not establish general coverage or hardware behavior.
