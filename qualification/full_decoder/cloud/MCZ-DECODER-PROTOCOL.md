# Experimental full Decoder follow-up — predeclared

Prerequisite met: source acbf69de3c7a8548919129d04826c1c8fe277f67 passed 42
complex-state, 158 sparse interference and 10 negative cases in the corrected
MCZ prototype experiment. The first enabled-state failure remains retained.
The qualified header SHA256 is fixed in patch_mcz.py.

One new independent CPU VM under unchanged PLAN.md bounds: m7i.large, 2 vCPU/8 GiB,
20-GiB encrypted disk, no inbound rules or IAM profile, 1200-second observation,
300-second cleanup. Same 180-second compilation and 60-second fixture limits.
No use of shared Docker or changes to platform/SDK checkout or local installed
libraries. The original 24-qubit/four-trial tiny fixture is unchanged.

The guest builds one experimental Core derivative from the exact merged source.
It retains the existing trace checkpoints and replaces only the observed MCZ
expansion for `sparse-sim` with the qualified Z-only metadata prototype. Every
other backend name retains the original expansion call. The prototype is not
installed or published as a general Circuit API. It is not used for serialization,
flattening or bit remapping in this full-fixture path.

Record original, trace-predecessor, derived source, unified patch and header hashes;
bind the loaded Core path/hash to the built derivative. Restore the public QFT
provider as in earlier probes, rerun 70 phase-sensitive QFT and six initialization
cases, then the unchanged tiny consumer. The reused installed dependencies retain
their own historical identities; current source SHAs do not imply they were rebuilt.

A completed caller result is checked by the existing consumer against the tiny
classical oracle. A no-improvement result is inconclusive. A later timeout or
other failure remains unqualified even if MCZ expansion is faster. Retain partial
output and the original deadline; no restart, replacement VM or time extension.
This is a diagnostic repair observation, not stochastic or full-Decoder proof.

Next gates remain: repair packaging into the Core fork, tests for broader IR and
backend boundaries, stochastic success, installed plugin/image and release/runtime
lock promotion. No hosted availability or main SDK/compiler dependency changes.

Pack with `pack.py NEW_DIRECTORY mcz-decoder`, then existing cloud/run.py with a
new run directory. Preserve failed and successful experiments separately.
