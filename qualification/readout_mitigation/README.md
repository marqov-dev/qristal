# Independent calibration and held-out readout mitigation

This protocol is fixed before native execution. It uses the existing public
Qristal/Aer CPU image as a bounded source overlay, not a new image build or
hosted execution path. No QB hardware or commercial Emulator is involved.

## Predeclared experiment

- Three stationary q0-only readout settings: (p10,p01) = (.05,.10), (.20,.10),
  (.40,.40). A (.50,.50) setting is a rejection control.
- Two independent calibration circuits per setting: prepared 00 and 10.
- Six held-out circuits at each non-singular setting: 00, 10, 01, 11, H on q0,
  and Bell. All 26 native executions use 16,384 shots and distinct seed values
  fixed in demo.schedule(). Shared calibration is reused across held-out circuits;
  they are not independent calibration repetitions or hardware observations.
- Estimate a=P(report 1|prepared 0), b=P(report 0|prepared 1) from calibration
  counts. The correction function receives those counts, never configured noise
  rates. Columns of the assignment matrix are true outcomes, rows observed:
  A = [[1-a,b],[a,1-b]]. Correct each fixed-q1 pair with the inverse of A.
- Require positive determinant d=1-a-b at least .10. Reject the near-singular
  control. This guards amplification and restricts the demonstrated profile.
- Validate raw outcome probabilities against independently derived analytic
  expectations within .025; require exact absence for zero-probability outcomes.
  Require each corrected outcome within .08 of its known ideal probability.
- Require at least 50% reduction in mean absolute observable error per setting,
  averaging the twelve errors from six held-out circuits and Z0/Z0Z1. This is a
  descriptive acceptance criterion fixed before execution, not a significance test.

Correction preserves signed quasi-probabilities, including negative values.
There is no clipping or projection. The analysis retains negative mass explicitly.
Perfect state preparation and a stationary, local classical readout model are
assumptions of this demonstration; drift, preparation error and correlated
readout are outside its validated scope.

## Uncertainty and chart

Plot held-out Z0Z1 estimates before/after correction against exact ideal targets,
one panel per non-singular setting. Show pointwise approximate 95% normal
intervals using a first-order delta method, including BOTH independent
calibration binomial variances and held-out multinomial sampling variance.
Intervals can extend outside physical expectation bounds and are not clipped.
They are not simultaneous coverage statements or uncertainty in a device model.

For O=Z0 or Z0Z1, let T=1 or Z1 respectively. The corrected expectation is
F=(mean(O)-(b-a)mean(T))/d. Its calibration derivatives are (mean(T)+F)/d for a
and (F-mean(T))/d for b. The held-out term is Var(O-(b-a)T)/(N d²).
Add the two squared derivatives times a(1-a)/Ncal and b(1-b)/Ncal.
Finite-difference tests independently check the derivatives.

## Existing methods reused

The assignment-matrix approach is documented by
[Qiskit Experiments](https://qiskit-community.github.io/qiskit-experiments/manuals/measurement/readout_mitigation.html)
and [IBM's M3 tutorial](https://qiskit.qotlabs.org/docs/tutorials/readout-error-mitigation-sampler).
[Aer ReadoutError](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.ReadoutError.html)
documents conditional-probability orientation. This is a transparent two-by-two
example, not a reimplementation or qualification of M3. No new mitigation
dependency is needed for this restricted model.

Run qualify.py with a new --output directory only when the qualified image is
already installed. It uses the existing non-root, network-free, read-only
container harness (2 CPUs, 4 GiB, 240-second bound), verifies removal, and retains
counts, source/options hashes and analysis. Analyze or plot the resulting JSON
offline without starting Docker.

## Recorded result

[The predeclared native experiment passed](../evidence/2026-09-12-readout-mitigation): 26 cases, with the singular control rejected. Mean absolute Z0/Z0Z1 error on held-out circuits fell by 95.64–96.03% across the three tested settings. [The chart](../conference/readout-mitigation) shows signed estimates and calibration-inclusive uncertainty. This result is limited to the stated simulation model; it does not qualify full SPAM or physical-device calibration.
