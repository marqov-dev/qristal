# Existing QPP lowering fails the exact complex-state reference

Source 1936671 compiled and passed 12 input rejections. After passing the first
layout's X/Y/Z/H modes, it failed controlled Rx(+0.37) inversion with error 0.282897.
The candidate metadata was lowered through the selected installed C-U service.
This is a native counterexample to treating that legacy lowering as an exact
complex-state reference. Root cause and broader gate coverage require further
analysis; this observation alone does not assign blame to all upstream releases.

The next candidate uses explicit projector/parity rotations for QPP. The legacy
20-case fallback inventory remains visible as diagnostic data; its mismatches are
not counted as successes. No tolerance or execution bound is enlarged. All exact
owned resources cleaned; public infrastructure IDs are consistently anonymized.
