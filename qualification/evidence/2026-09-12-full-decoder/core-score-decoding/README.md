# Core score conversion: source-bound standalone evidence

[Core PR #3](https://github.com/marqov-dev/qristal-core/pull/3) replaces the decimal
intermediate with a checked binary accumulator. `11111111111` represents binary
2047 but decimal 11,111,111,111, exceeding 32-bit signed int. This counterexample
is a source/arithmetic finding; no particular undefined old-runtime output is
claimed.

4,110 production-helper checks passed on macOS with Release flags and address/
undefined-behavior sanitizers. Full search source syntax checking passed with
its existing CMake bundle define and libc++ compatibility switch. Initial host
compile diagnostics and their corrections are documented with the source tests.
No native XACC linking, installed plugin replacement or simulator execution was
performed. Runtime source locks remain unchanged.

Decoder PR #2 is merged at 77684195ad9e0fa758a4caf3fe49875327f4b4b1. The evidence
batch Qristal PR #23 remains open. A separately predeclared tiny caller-contract
smoke is prepared in `qualification/full_decoder/NEXT-NATIVE.md`; it has not run.
