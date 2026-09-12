# Full Decoder register and score safety follow-up

43 production-helper checks passed in a native macOS Release compile with
AddressSanitizer and UndefinedBehaviorSanitizer. This is a small standalone C++
program, not an XACC-linked simulator run. Source hashes and command are retained.

Covers the historical 80-qubit layout, each missing/overlapping/negative register,
high IDs, insufficient ancilla, timestep dimensions, symbol capacity, score
precision, dense permutations and score encoding including values above 15.
The old score bitset used sizeof(int) as a bit count, producing four bits for a
six-bit score register in the historical fixture.

The Decoder branch also replaces static named backend ownership, invalidates
failed initialization, rejects unsupported methods/invalid explicit backends,
and adds XACC integration tests. These integration changes have **not** been
executed against XACC at this revision. The earlier three native tests refer
only to ac2ad41, not this follow-up. No installed plugin or image was replaced.

Host syntax checks of the full source and new integration tests succeeded with
`-D_LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION`. The first syntax attempt
without that documented libc++ compatibility switch failed in existing
CppMicroServices headers using removed std::unary_function. The retry retained
deprecation warnings. Syntax checking is not linking or runtime qualification.

New Docker work remains deferred for managed-platform release qualification.
