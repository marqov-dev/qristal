# Initial inverse attempt: QPP metadata assumption rejected

Source bf95ddb compiled and passed 12 rejected-input checks. Native QPP failed
layout 0 / operation X / nested mode with complex error 0.0428301. The nested
inverse includes controlled Ry. The selected public QPP visitor only shortcuts
controlled X/Y/Z; unsupported empty controlled blocks have no fallback leaves
and are therefore skipped. Sparse-sim supports the broader seven-gate subset.

This was our prototype's incorrect cross-backend assumption. There is no new
evidence that private QB libraries are needed. The corrected experiment adds an
explicit QPP decomposition step, retains the matrix tolerance, and tests direct
sparse inversion independently as well as through roundtrip checks. No full
Decoder run or passing whole-matrix claim comes from this attempt. All exact
owned resources cleaned; public infrastructure IDs are consistently anonymized.
