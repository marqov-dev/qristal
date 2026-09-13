# Full Decoder stage trace — predeclared

Tracking: platform #2173; parent #1701. Conference preparation is independent #2172.

Run one isolated CPU VM using the unchanged PLAN.md infrastructure bounds and
24-qubit/four-trial tiny fixture. Retain all QFT and six initialization gates.
The Decoder timeout stays 60 seconds; compilation stays 180 seconds per stage.
No algorithm, backend, seed policy, threshold or iteration-limit change is made.

The only Core change is flushed monotonic diagnostic output. The instrumenter
requires the exact merged source SHA256 and verifies that deleting its marked
insertions reproduces the original bytes. Source, resulting source and unified
patch hashes are recorded in search-trace-identity.json and the native report.
The Core and Decoder source checkouts and installed local runtime are untouched.
Only the guest's rebuilt Core library contains the diagnostic insertions.

Observe paired checkpoints for inverse state-preparation expansion, used-bit
collection, MCZ expansion, amplitude-amplification cloning and backend execution.
Record used-bit/control counts and top-level instruction counts; these are not
flattened gate counts. MCZ begin with no end before timeout localizes the stalled
stage but does not, alone, distinguish memory pressure from CPU synthesis cost.
Timing includes diagnostic overhead and is not a performance benchmark.

Retain timeout output, original exception, exact binary identities and all
cleanup receipts. If a different earlier stage fails, retain that failure and
make no search conclusion. If a result completes, apply the existing caller
contract and oracle gates; do not infer stochastic correctness from one result.
No retries, replacement host or extended deadlines within this experiment.

A separately reviewed repair must follow measured evidence. This experiment does
not qualify the installed Decoder plugin, promote the runtime lock, change shared
platform/SDK code, enable hosted jobs or require main-agent interruption.
