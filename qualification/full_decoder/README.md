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
