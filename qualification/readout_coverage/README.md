# Synthetic interval coverage protocol

Predeclared at merged baseline badeaca7f89a5324c7ebc228d193aee3ff1ab011.
This tests the existing estimator's approximate 95% interval under repeated
synthetic sampling. It is not a Qristal/native simulator or hardware experiment.

Use Python >=3.12 standard-library Random.binomialvariate. Sequential conditional
binomial sampling generates multinomial counts; retain interpreter version,
seed2026091301, all counts and source hashes. No dependencies or native compute.

Five scenarios: stationary calibration/measurement noise (.05,.10), (.20,.10),
(.40,.40); stale calibration (.20,.10) with measurement noise (.35,.10) or
(.05,.025). For each scenario and zero/Bell fixture, run 1000 independent
calibration-plus-held-out repetitions, 16384 shots per preparation/sample.
The two fixtures each have ideal Z0Z1=+1. Do not reuse calibration across repetitions
or fixtures. Probabilities are explicit analytic formulas independent of the
estimator's forward-model helper.

Report coverage of the ideal value by the existing calibration-inclusive
delta-method interval, mean signed bias and mean estimated SE. Wilson95 intervals
describe Monte Carlo uncertainty in coverage, not uncertainty of the physical
model. Do not clip estimates or intervals. No empirical pass threshold or
post-hoc scenario selection: report all results, including undercoverage.
Coverage near nominal here does not establish other observables or noise models.
The stale scenarios intentionally violate stationarity; their intervals account
for sampling variance, not systematic calibration bias.

Commit this protocol before execution. Run study.py --output NEW_DIRECTORY.
A fresh synthetic study is optional; replay retained counts without random
sampling using the checker. Native drift protocol remains separately pending.
