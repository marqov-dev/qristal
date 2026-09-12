# Native independent readout calibration — 12 September 2026

Protocol, acceptance thresholds and plotting method were committed before execution
at 36f92e1bd31a2d12224527d4715c50bada5f8fd6. No threshold was changed after observing
the result. The existing public Qristal/Aer CPU image ran 26 native cases:
eight calibration executions and eighteen held-out executions, each with 16,384
shots and distinct predeclared seeds. One non-root, network-free, read-only
container was used under the existing 240-second harness. Removal was verified.
No build, dependency installation, cloud job or hosted submission was performed.

| Configured p10 / p01 | Measured p10 / p01 | Mean absolute observable error, raw → corrected | Reduction |
|---|---|---|---|
| 5% / 10% | 4.956% / 9.698% | 0.124481 → 0.004936 | 96.03% |
| 20% / 10% | 19.971% / 10.181% | 0.255910 → 0.011163 | 95.64% |
| 40% / 40% | 39.868% / 39.948% | 0.599192 → 0.024188 | 95.96% |
| 50% / 50% control | 49.823% / 49.634% | Correction rejected | determinant 0.005432 < 0.10 |

Mean error averages Z0 and Z0Z1 absolute errors across all six held-out circuits
at each setting. This is a descriptive summary, not an accuracy percentage,
fidelity, hardware improvement or significance test. The predeclared acceptance
criterion was at least 50% aggregate error reduction per setting; all three
settings passed. All raw forward-model and corrected-outcome checks passed.

The corrector estimates its matrix only from calibration samples. Configured
noise rates are used by the simulator and independent validation, not by the
correction function. Calibration and held-out circuits use distinct seeds.
A calibration matrix is shared within each setting, so the resulting errors
are correlated and are not independent calibration repetitions.

Signed quasi-probabilities are retained without clipping; the largest negative
mass was 0.016934. Stronger noise amplifies uncertainty, shown in the chart.
Pointwise approximate 95% normal intervals include both calibration and held-out
sampling variance via the predeclared delta method. They are not simultaneous
coverage guarantees or estimates of physical-device/model uncertainty.

The model assumes ideal state preparation and stationary independent classical
readout noise on q0 only. This is not full SPAM mitigation, correlated/device
noise qualification, commercial QB Emulator behavior or hosted Marqov execution.

Raw records, exact program/options hashes, native stdout, analysis and cleanup
are retained. manifest.json binds the data bytes, image and overlay source hashes.
Run qualification/readout_mitigation/check_evidence.py with this directory as its
argument to replay without Docker. Thirteen method/evidence tests cover matrix
orientation, inversion, negative estimates, uncertainty derivatives, conditioning,
seed separation, count/hash binding and cleanup identity.

The [figure and provenance](../../conference/readout-mitigation) retain the
before/after parity plot. Its exact ideal target markers are analytic references,
not additional measurements. The [protocol](../../readout_mitigation) links
standard upstream assignment-matrix methods and states the full limitations.
