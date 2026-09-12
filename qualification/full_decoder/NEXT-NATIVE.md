# Native qualification gate — original local protocol

The [independent CPU VM protocol](cloud/PLAN.md) is the subsequent alternative
for the shared-Docker hold. It has separately declared build/runtime limits and
does not replace the installed-plugin qualification required below. Consult its
retained outcome before treating any stage as complete.

Decoder PR #2 merged at 77684195ad9e0fa758a4caf3fe49875327f4b4b1.
Core score conversion merged at bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a (tested source 5f8d447).
Decoder threshold-order review source: 24fc468b47500692350b7e8e1656c1d28dec4aa8.
Do not advance the installed-runtime source lock on the strength of standalone
checks. The release lane still has priority over shared local Docker.

1. Repeat `input_probe.py` against the explicitly selected Decoder source, including the threshold-order repair. Its fixed
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

The input probe now fingerprints its source, both helper headers, class header and
test source before/after execution. Qualification requires all six named tests,
successful process status, unchanged identities and verified exact-owned cleanup.
Docker inspection/removal calls have 20-second bounds; cleanup failure remains
unverified and is retained instead of being mistaken for successful removal.
The CLI exits nonzero for timeout, missing tests, changed source or failed cleanup.
Seven offline tests cover these acceptance/cleanup controls; they do not launch
Docker or establish native cleanup behavior under a daemon outage.
