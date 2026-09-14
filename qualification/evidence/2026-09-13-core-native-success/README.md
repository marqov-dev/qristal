# Source-built Core: native QPP success

The user approved one bounded CPU experiment against PR44, merged as
`ed67f49cfe3f92aa4e9e94934403f15ca5c1de7d` (executed tip
`490a262eb13a1940de80253260b7023146e121ec`). All 20 native stages passed.
Core configure took 5.98 seconds and build took 438.36 seconds on m7i.large.
Installed-only C++ and Python each passed identity and Bell at 256 shots:
**two distinct circuits, four API executions**. The separate retained XACC
consumer replay passed four ACZ interference fixtures and Bell. Source selection,
post-build source audits, plugin normalization and installed linkage checks passed.
The original 3,829 XACC entries were unchanged; nine declared plugin links were added.

The input archive was 314,256,512 bytes, SHA256
`866891b7be3033008786a0f197ca0a31b8d5ac42e87d106564f31c7a8db9960f`.
Locked Core source was `a5c3e5fa544c07d538974d3a289b19652d483848`;
its reviewed derivative SHA was
`6ab2ab67c277275b21878742d0088cb4337626336cbb088b310ab92b2e4c75bf`.
`protocol.json` and `executed-guest.py` preserve the actual experiment inputs;
the compact console implementation in this PR was NOT run in this VM.

## Artifact recovery and limits

The successful full output was uploaded before console emission. The full console
report exceeded the 20,480-character envelope bound, yielding `report_bounds`.
Original console and retention failure records are preserved unchanged. The
supervisor terminated the VM and retained the transfer bucket for recovery.

Recovery used authenticated S3 GET with exact account/bucket ownership tag,
conditional ETag selection, bounded size/time, matching response size/ETag, and
file/directory fsync. ETag was object selection evidence, not an asserted SHA256.
The recovered archive was then independently checked by the unchanged output
verifier and native classifier: 5,703 entries verified; all 20 stages passed.
**The original console-to-artifact hash binding was unavailable.** This is
explicit alternate provenance, not reconstruction of that missing binding.
`recovery-verification.json` records this distinction. Its cleanup-pending flag
is an earlier snapshot; `cleanup-summary.json` records final independent checks:
VM, attached volumes, security group and private transfer bucket are absent.
Raw authenticated download and cleanup records remain locally retained. Ephemeral
resource IDs and credentials are not published here; the executed protocol retains
the non-secret account ID so its original hash remains replayable.

The 26,868,891-byte full artifact SHA256 is
`bbfe86d11afc5ed5fe827d68f78c5fada27f1aa7827bc23ca9e4f4d02bae3c85`.
It is durably retained outside temporary folders at
`/Users/david/Marqov Artifacts/qristal/core-native-2026-09-13/output.tar.gz`
with protocol, materials, original console, recovery and cleanup records.
It is deliberately not committed as a compiled binary or published runtime.

`stage-logs.tar.gz` contains only the exact full stage logs copied from that
archive. Replay with `python3 -B qualification/evidence/2026-09-13-core-native-success/replay.py`.
This checks stage/log/protocol consistency, not the full installation archive;
full archive verification requires the retained binary and material manifest.

## Packaging and next gate

The existing output verifier, native classifier and packaging input gate all
accepted the full artifact. `packaging-gate-summary.json` preserves the false
console binding. This establishes packaging input readiness, not a built or
qualified runtime image. Next: assemble a QPP-scoped runtime preserving sibling
Core/XACC paths, rebuild Python offline from 50 locked wheels and retained ANTLR,
then test it without source/build mounts. ABI dependencies, licenses/notices and
redistribution review remain packaging work. Aer/noise, Integrations, Decoder,
GPU source builds and hosted admission are separate gates. Historical CPU/GPU
binary demonstrations are not retroactively source-built by this result.
