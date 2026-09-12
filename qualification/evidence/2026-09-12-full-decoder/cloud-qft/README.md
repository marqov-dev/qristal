# Public QFT diagnostic — compiled, tiny runtime timed out

12 September 2026, guest/launcher revision `a3fdd56`. The predeclared third
experiment used the same Core/Decoder revisions and public XACC
`d1edaa7ae53edc7e335f46d33160f93d6020aaa3`. Source hashes, commands and binary hashes
are retained in `result.json`. Archive SHA256:
`e613b4dd5ada87ff15609043f181f111cd9cf1c56ecc8c66e95de0718c341cf5`.

The qualification-only QFT/IQFT provider built and bundled successfully, using
unchanged upstream implementations. The Core bundle and both Decoder executables
also compiled. All six named initialization tests passed again; these are repeat
runs of six cases, not eighteen distinct cases across three experiments.

The tiny fixture hit `ProcessError:process_timeout` at its original 60-second
limit. No candidate, caller-contract pass or final service-availability result
was retained. The capture helper discarded partial output on failure, so this
evidence cannot establish whether execution passed the QFT checks, reached
simulation, or stalled elsewhere. Successful provider compilation is not a
runtime compatibility verdict. The earlier missing-iqft diagnostic remains in
the preceding run; this timeout does not prove that every dependency is restored.

Observation and cleanup completed automatically. The exact instance terminated,
its recorded disk and security group were absent, and the private transfer
object/bucket were deleted and absence verified. Both failure and original
deadlines are retained. No native experiment follows this third diagnostic in
this batch; there is no time-limit extension or source-lock promotion.

The subsequent harness repair adds **opt-in**, byte-bounded partial output on
timeout/overflow, with offline regression tests. Existing callers keep the prior
discard behavior. This repair was not present in this run and cannot recover its
lost output retroactively.

Next bounded tasks:

1. Preflight required instruction/algorithm/backend services and capture flushed,
   timestamped stage checkpoints before any full Decoder search. Preserve failure
   output; keep the same 60-second fixture limit.
2. Qualify the unchanged public QFT/IQFT provider independently on small analytic
   forward/inverse fixtures before choosing a permanent generators dependency.
3. After a complete small caller-result observation, compare against the exact
   classical oracle and qualify stochastic success behavior separately. Only then
   consider installed Decoder-plugin and runtime-image/source-lock advancement.

The conference's existing CPU noise, simplified Decoder and standalone GPU
results remain separate. Full Decoder remains an open qualification task.
