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

## Register/score follow-up

[43 host sanitizer checks](../evidence/2026-09-12-full-decoder/register-safety/README.md)
cover the production register/score helper at Decoder b34a94b. Expanded XACC
integration execution remains pending, distinct from the earlier table-only
native pass. [Proposed result contract](RESULT-CONTRACT.md) records why an
upstream score threshold and sampled string cannot always be forwarded as a pair.

The result accumulator and caller metadata are implemented at Decoder 4d330ba;
[53 standalone checks and syntax evidence](../evidence/2026-09-12-full-decoder/result-publication/README.md)
pass. The expanded native integration remains deferred, and the Core integer
conversion concern is unresolved. These repairs are bundled in Decoder PR #2.

## Core dependency follow-up after Decoder merge

Decoder PR #2 merged at 77684195. [Core PR #3](https://github.com/marqov-dev/qristal-core/pull/3)
repairs the binary-score decimal-overflow path; [4,110 standalone checks](../evidence/2026-09-12-full-decoder/core-score-decoding/README.md)
pass without Docker. Runtime/plugin qualification remains pending. The
[next native protocol](NEXT-NATIVE.md) and tiny result-contract consumer are
prepared and syntax-checked, not executed. No source lock is advanced yet.

## Comparator-order and evidence-gate follow-up

Core PR #3 is merged. [Decoder PR #3](https://github.com/marqov-dev/qristal-decoder/pull/3)
fixes the threshold register's MSB/LSB mismatch; [4,216 standalone checks](../evidence/2026-09-12-full-decoder/comparator-order/README.md)
pass on macOS/Linux. Seven new offline acceptance/cleanup tests strengthen the
next input probe without claiming another native run. The full selected offline
replay now passes 152 tests. Expanded linked/plugin execution remains deferred.

## Independent cloud native follow-up

The [first isolated CPU VM](../evidence/2026-09-12-full-decoder/cloud-initial/README.md)
compiled the merged Core search plugin and both Decoder programs. All six named
XACC-linked initialization tests passed. The tiny program failed before simulation
because the new harness omitted CMake's post-link bundle archive. Cleanup required
resuming the same supervisor and was then verified, without a replacement VM or
deadline extension. A [separate packaging correction](cloud/BUNDLE-FOLLOWUP.md)
restores that step; full Decoder correctness remains unqualified.

After merged PR24, [70 native QFT/IQFT cases passed](../evidence/2026-09-12-qft-states/README.md),
including independent complex-amplitude and round-trip comparisons. The next
tiny Decoder trace retained qft/iqft availability and entry into exponential-search
iteration 1 before the same 60-second timeout. No candidate or caller-result pass
was retained. [The next source diagnostic](cloud/SEARCH-HOTSPOT.md) separates
inverse expansion, reflection synthesis, cloning and backend execution before
selecting a repair. No additional native run or time-limit extension followed.
