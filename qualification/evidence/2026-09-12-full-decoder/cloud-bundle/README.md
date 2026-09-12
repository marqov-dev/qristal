# Bundle-corrected CPU VM — library loaded, public iqft service missing

12 September 2026. Guest and launcher revision: `4c2586d`.
Core/Decoder sources remain `bd3a8e28` / `a58df0cf`.
Archive SHA256: `3b49b3760bc1530a9e4eedcea81c5c8e5ca4ab23261308f1fe1843c9f888560d`.

The added original post-link resource-compiler step succeeded. The program's
loaded-object enumeration observed
`/work/install-xacc/plugins/libalgorithm_es.so.1.8.1`; its guest file hash matches
the rebuilt bundled library:
`d55bb9e44c199a0356931845338640ce9a9a7fa48db87412db7130f0cdf26207`.
This resolves the first probe's bundle-loading failure. The later runtime failure
means the final pass gate was not reached; the matching mapping/hash are retained
observations, not an overall qualification pass.

Both Decoder programs compiled and all six named initialization tests passed.
The tiny program entered Decoder circuit construction, reached QPrime, reported
`Could not find iqft in Service Registry`, and exited 139 with a segmentation
fault. It did not return a candidate or pass the caller-result contract.

Public XACC contains QFT and IQFT in its generators bundle. The selected installed
prefix lacks `libxacc-circuits.so`; Core phase estimation requests iqft and
dereferences the resulting service. This is a missing public runtime component,
not evidence of unavailable commercial QB libraries. The source trace and next
bounded diagnostic are in [QFT-FOLLOWUP](../../../full_decoder/cloud/QFT-FOLLOWUP.md).

This VM automatically completed observation and cleanup. `cleanup.json` records
termination of the exact instance and absence of its recorded disk and group;
`transfer.json` records deletion/absence of the private artifact bucket. The
cleanup improvement accepts omitted subnet only for an already-bound retiring
instance with the same client token; running/unbound identities remain rejected.
No deadline extension, replacement launch or shared Docker work occurred.

Reports preserve commands, source/binary hashes and bounded logs. The complete
checksummed console payload is replayable offline. No runtime image, source lock,
installed Decoder plugin or hosted capability is promoted by this result.
