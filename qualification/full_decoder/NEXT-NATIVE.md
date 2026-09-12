# Next native qualification gate — predeclared, not executed

Decoder PR #2 merged at 77684195ad9e0fa758a4caf3fe49875327f4b4b1.
Core score-conversion review source: 5f8d4474648c35f61c0bae20c3d6d0455dbfff3d.
Do not advance the installed-runtime source lock on the strength of standalone
checks. The release lane still has priority over shared local Docker.

1. Repeat `input_probe.py` against the merged Decoder source. Its fixed
   180-second compile-and-test limit remains; run only expanded initialization
   tests, not historical algorithm fixtures. Record source/header hashes and
   the complete compiler command. A harness exit zero is not test success unless
   the retained test exit/status and assertions confirm it.
2. Rebuild the changed Core search plugin and Decoder in an isolated build/output
   location, preserving the existing installed prefixes and historical artifacts.
   Pin and retain the resulting library identities. Do not reuse the old broad
   parent-directory writable build harness or overwrite earlier logs.
3. Run `tiny_result_smoke.cpp` once with a precompiled binary in one nonroot,
   network-disabled, read-only container: 2 CPUs, 4 GiB, 256 PIDs, 60 seconds,
   bounded output. No retries or deadline extension after observing the outcome.
   Use exact owned-container cleanup with absence verification on every exit.

The tiny fixture uses one timestep, two symbols, one metric bit, 15 ancilla and
24 qubits total, with four canonical search trials on sparse-sim. Input [0,1]
has classical beam `1` with probability one. This removes the multi-timestep
collapse ambiguity from the first caller-result check.

Acceptance is separated:

- Invalid initialization, malformed result metadata, an out-of-range score or an
  improving candidate inconsistent with raw string `1`: fail the smoke check.
- Four completed trials with no improvement and explicit empty candidate:
  caller-contract execution only; algorithm outcome is inconclusive.
- An improving candidate with positive in-range score and raw string `1`:
  a single oracle-consistent observation, not a success-rate or full-algorithm
  correctness claim. Integer score is not interpreted as a probability.
- Timeout: retain inconclusive execution plus cleanup; no larger limit is chosen
  after seeing it. No full Decoder capability is marked complete.

Core score parsing also needs linked/plugin validation; standalone arithmetic
checks alone do not prove that the rebuilt plugin was the one loaded. Retain
loaded library paths and hashes before accepting any new installed-runtime claim.
