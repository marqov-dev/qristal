# Full Decoder result contract and next bounded test

Source audit: Decoder b34a94baa5bf4136d7021210a774d068c47d8126 and Core
a5c3e5fa544c07d538974d3a289b19652d483848. The initial audit was a proposal. Decoder 4d330ba now implements the
caller metadata and maximum-pair accumulator below; native integration remains
unverified. This does not change the platform execution contract.

## Why forwarding existing fields is insufficient

Core `src/algorithms/exponential_search/exponential_search.cpp:317` publishes a
measured score/string when the score improves. Its non-improving branch at line
321 instead publishes the old threshold and the newly sampled string. Those
fields need not describe the same candidate. Decoder currently tracks only
strict improvements and never publishes them to its caller. It also overwrites
the current threshold each trial while separately tracking a maximum.

Implemented review-branch output: explicit initial threshold, best observed improving score,
raw encoded string, whether an improving candidate was observed, trials attempted
and method. Publish a score/string pair only from the same strict-improvement
observation. If no improvement occurs, return an explicit no-improvement state;
do not claim the threshold's corresponding string was found. A raw encoded
string is not a decoded beam or a normalized probability. Preserve score
quantization and bit-order metadata before exposing a human-readable answer.

## Bounded tests before native algorithm qualification

1. Pure result-reduction tests: increasing/decreasing/equal scores, a high initial
   threshold, no improvement, and malformed/missing result fields. Check that
   maximum score and string remain bound to the same observation.
2. XACC-linked initialization tests for the current safety revision, with explicit
   per-instance named-backend routing and backend lifetime. Rebuild the installed
   plugin only after these pass; retain identity and cleanup evidence.
3. Use a deterministic tiny full-algorithm case before the historical two-row
   probabilistic fixture. Set limits before execution; retain timeout as a result.
   Compare decoded beam semantics to the exact classical oracle, but do not
   compare a quantized internal integer score directly to beam probability.
4. Only then qualify repeated probabilistic behavior against a predeclared
   statistical acceptance rule. A single sampled best string is not correctness.

Additional source concern: Core converts a binary digit string through `atoi`
before reconstructing its value (same file, around line 300). Long binary strings
can exceed decimal int range even when the eventual binary value fits. Audit
and test this separately before advertising broader score widths. The current
30-bit Decoder width guard prevents its own signed-score overflow; it does not
qualify this Core conversion or the full arithmetic circuit.

No main-agent action, hosted enablement or release dependency is requested.

## Current implementation and validation

After all trials complete, the caller receives `initial-score`, `best-score`,
`best-string`, `has-improving-candidate`, `trials-completed`, `method`, and
`result-kind=quantized-search-observation`. No-improvement returns the initial
threshold with an empty string and false candidate flag. Raw bits remain raw;
there is no decoded-beam or normalized-probability claim.

The ten result-reduction checks are now part of 53 passing standalone sanitizer
checks. XACC-linked execution, plugin rebuild and the bounded oracle comparison
remain next. The Core atoi conversion is repaired in review source 5f8d447 (Core PR #3), with 4,110 standalone sanitizer checks. Linked/plugin qualification remains unresolved.
