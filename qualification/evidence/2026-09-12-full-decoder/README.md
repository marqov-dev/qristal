# Full Decoder bounded diagnostic

The existing `QuantumDecoderCanonicalAlgorithm.checkSimple` fixture at Decoder
13bb8f80f98bd259196834a13817c23ec02480e6 reached the predeclared 60-second
limit. Its owned container was removed and absence verified. The fixture has no
active decoded-answer assertion, so neither timeout nor a hypothetical PASS
would establish correctness. No timeout extension was attempted.

The capture helper discards partial output on timeout. No stdout/stderr from
this attempt is retained; `result.json` records the timeout, not an algorithm
failure. The harness process itself exited zero after writing that result.
Source and binary identity and resource limits are retained in `intent.json`.

This does not invalidate the separately qualified simplified Decoder.
