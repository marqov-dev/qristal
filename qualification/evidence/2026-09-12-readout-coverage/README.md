# Synthetic calibration coverage study

This is synthetic multinomial sampling, not a native Qristal or hardware result.
Protocol/source was committed before execution; see manifest.json for exact
revision, Python3.14.4, seed and hashes. All 10,000 repetition records are retained.

Stationary zero/Bell interval coverage at low, medium and high readout noise:
95.7/94.5%, 94.9/96.5%, 94.3/94.8%. Each uses 1000 independent calibration and
held-out samples. The medium/Bell Wilson interval is 95.17–97.47%, excluding
nominal95%; this is reported without retuning or a blanket calibration claim.
Ten pointwise intervals are not a simultaneous test.

Both stale scenarios had 0/1000 covered intervals for each fixture; the pointwise
Wilson upper limit is approximately0.383%. Mean signed biases were approximately
-0.428/-0.214 for increased noise and +0.429/+0.322 for improved noise (zero/Bell).
The estimator preserved values beyond physical bounds instead of clipping them.

The result demonstrates that sampling-only uncertainty misses systematic bias
when calibration is stale. It does not establish real-time device drift,
general coverage, or failure of the native simulator. The 40-case native
stale/fresh experiment remains pending separately.

Run python3 qualification/readout_coverage/check_evidence.py to replay retained
counts and verify hashes. Raw counts permit independent statistical analysis.
