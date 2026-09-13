# Initial profile attempt: diagnostic report unavailable

Prepared source `ef8865a` ran on one independently owned CPU VM. The recovered,
checksummed result contains only `bootstrap_exit_code: 1`. It does not establish
which compile or runtime stages completed. No native profile or passing test
claim can be made from this attempt.

The guest could previously raise while encoding its final report if the fixed
120,000-byte / 128-by-160-character evidence envelope was exceeded. The preceding
Decoder report already used 16,564 encoded characters of the 20,480-character
limit. Additional per-gate timing rows make payload overflow plausible, but the
retained bootstrap marker does not prove this was the cause.

A separately declared follow-up reduces checkpoints from every 16,384 to every
65,536 visited nodes and emits a compact stage-status diagnostic if the envelope
is still exceeded. It does not extend simulation time or alter the fixture.
All exact instance, disk, security-group and transfer cleanup checks passed.
