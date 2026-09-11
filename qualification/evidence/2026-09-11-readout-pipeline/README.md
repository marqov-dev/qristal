# Restricted CPU readout pipeline — observed qualification

The public CPU image, with a Python source overlay, passed **27 test methods** and
**11 native Aer analytic fixtures** on 2026-09-11. Eight additional offline evidence
checker tests pass. No QB private repositories, commercial plugins, GPU, AWS jobs,
image rebuild or registry publication were used.

Base Qristal source: `a3869eae904bf2d0469468c54513031a52cb5ea8`, plus the exact
source files hashed in `manifest.json`. Native image:
`sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44`.
The base commit identifies inspected main; the overlay changes were uncommitted
when tested and are identified by their recorded hashes. Image identity pins the
existing compiled dependencies; this is not another from-source rebuild claim.

`tests.stderr` records all 27 unittest methods passing, with existing Qiskit 0.46
deprecation warnings retained. Tests cover the new closed noise options and failure
handling, unchanged ideal pipeline, restricted parser, local preparation bindings,
result candidate validation and bounded subprocess behavior. The native analytic
matrix is in `demo.stdout`; it has no stderr. Both run-owned containers were
removed, with intent and cleanup records retained. An earlier setup-only attempt
found Docker refuses file copying into a read-only root; the final harness instead
writes its overlay into bounded tmpfs. That attempt never started the simulator.

## Analytic matrix

Each case uses **16,384 shots**. Deterministic cases require exact counts;
probabilistic cases have a predeclared absolute tolerance of **0.025** per outcome.
The asymmetric cases each run with seeds 7 and 42. These fixed small circuits
qualify the specified behavior, not application-scale accuracy or performance.

| Circuit / noise | Expected probabilities (logical qubit zero first) |
| --- | --- |
| Zero / no error | `00: 1` |
| X on q[0] / no error | `10: 1` |
| Zero / p10=p01=1 | `10: 1` |
| X on q[0] / p10=p01=1 | `00: 1` |
| X on q[1] / p10=p01=1 on q[0] | `11: 1` |
| Zero / p10=.2, p01=.1 | `00: .8`, `10: .2` |
| X on q[0] / p10=.2, p01=.1 | `00: .1`, `10: .9` |
| Bell / p10=.2, p01=.1 | `00: .4`, `10: .1`, `01: .05`, `11: .45` |

The offline checker independently checks the fixed cases, canonical program hashes,
exact options bytes, backend, shot totals, bit order and tolerances. Its rejection
tests cover corrupted/missing evidence and rehashed changes to noise, canonical
identity, tolerance, fixture coverage and outcome probabilities. It performs no
execution. Manifest hashes provide consistency, not signatures or authentication;
an actor who controls the evidence, manifest and checker can fabricate a run.

## Remaining scope

The new helper exposes only readout error on qubit zero through the restricted
parser. Prior lower-level amplitude-damping/depolarizing observations remain in
[the native noise evidence](../2026-09-09-noise/); they are not added to this API.
There is no SPAM mitigation, full device noise model, GPU/tensor execution, commercial
Emulator/vQPU behavior, hosted acceptance, real database recovery or platform backend
registration in this result. The original ideal-only helper and its existing image
are preserved. Distribution of a newly packaged image and hosted contract admission
remain separate work.

Reproduction and offline commands are in [the runtime guide](../../runtime/README.md#restricted-readout-noise-demo).
