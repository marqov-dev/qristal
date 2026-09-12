# Full Decoder baseline probe

Predeclared diagnostic, not correctness qualification. Run the existing
QuantumDecoderCanonicalAlgorithm.checkSimple fixture at Decoder
13bb8f80f98bd259196834a13817c23ec02480e6 using the previously compiled
CITests_decoder and public toolchain432131e2. Source and binary hashes retained.

The fixture uses two timesteps, binary symbols, three metric bits, four trials
and sparse-sim. Its only result expectation is commented out. A zero exit/PASS
therefore establishes execution only, not decoding accuracy.

Source audit: initialize indexes probability_table[0] before emptiness validation;
named accelerator is function-static; execute creates a local buffer that shadows
the caller's buffer and does not publish the final best score/string to it.
The canonical search is hardcoded regardless of the advertised method parameter.
These are source findings, not all native-reproduced defects.

One read-only, no-network toolchain container,2CPUs/4GiB,256PIDs,
60-second execution limit and bounded output. Mount only existing build and
installed prefixes read-only at their original paths. No compilation, dependency
installation, shared platform/SDK files or AWS resources.
Retain any failure or timeout; do not broaden the limit after seeing the result.

## Observed diagnostic and bounded repair

The baseline fixture timed out at 60 seconds; cleanup was verified. See
[retained diagnostic](../evidence/2026-09-12-full-decoder/README.md). Partial output
was not retained by the bounded capture helper on timeout.

`input_probe.py OUTPUT_DIRECTORY` compiles the full Decoder source directly with
its new input-validation tests under `-DNDEBUG`, then runs only
`FullDecoderInputValidation.*`. It uses the already installed XACC headers and
libraries and cached GoogleTest objects; it does not replace installed plugins.
Its independent 180-second bound covers compilation and tests together. The
valid-input checks exercise initialization only, not full algorithm execution.
The toolchain and local cache layout are explicit in the retained command.

Further work must separate register validation/backend ownership, caller result
publication, and an independent classical beam-probability oracle. A safety fix
must not be reported as full Decoder correctness or application-scale support.

The native input-validation build passed all three tests; see
[input-validation evidence](../evidence/2026-09-12-full-decoder/input-validation/README.md).

`oracle.py` independently enumerates at most 4096 classical paths with exact
rational probabilities. Six tests cover the historical fixture (blank 0.14,
beam `a` 0.86), a case where the best path differs from the best beam, collapse
order, multiple symbols, normalization and invalid inputs. This is a reference
calculation, not native Decoder output. It intentionally accepts exactly
normalized decimal/rational input, unlike the native float tolerance.
