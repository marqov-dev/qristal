# Threshold order: source evidence and standalone regression

Decoder's threshold was prepared MSB-first while CompareGT was explicitly given
`is_LSB=true`. A six-bit threshold 1 therefore represented 32 to that comparator;
zero/palindromic patterns could mask it. The new register-preparation helper
reverses the formatting string to match the declared comparator convention.
Core's existing comparison-grid test already prepares LSB-first registers this
way. See Core `src/circuits/compare_gt.cpp` and
`tests/circuits/CompareGTCircuitTester.cpp` at a5c3e5f.

4,216 standalone production-helper checks pass on macOS under Release flags and
ASan/UBSan, and on Linux CI. Coverage includes all 64 six-bit thresholds and all
4096 classical comparison boundaries, existing register/score/result checks, and
non-palindromic/high-bit cases. These are mapping/arithmetic tests, not execution
of the quantum comparator. Full Decoder source syntax checking also passes.

[Decoder PR #3](https://github.com/marqov-dev/qristal-decoder/pull/3) is the new
review change; Decoder PR #2 and Core PR #3 are already merged. Native linked
execution remains pending under the release lane's resource hold. No runtime
image, source lock, hosted route, platform or SDK file changed.
