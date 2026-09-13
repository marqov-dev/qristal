# Independent CPU VM probe

This is an operator-owned native experiment, separate from hosted execution and
the shared local Docker environment. Read [the predeclared plan](PLAN.md) first.
The runner has fixed account, region, AMI, subnet, instance type and deadlines;
it is deliberately not a general provisioning interface.

Recorded sequence: [initial bundle failure](../../evidence/2026-09-12-full-decoder/cloud-initial/README.md),
[bundle-corrected missing iqft](../../evidence/2026-09-12-full-decoder/cloud-bundle/README.md),
[public QFT diagnostic timeout](../../evidence/2026-09-12-full-decoder/cloud-qft/README.md).
All six initialization cases passed. No full Decoder or caller-result pass was
obtained. All three VMs, exact disks/groups and transfer buckets were cleaned;
the first needed supervisor resumption, the next two completed automatically.
Current source includes the QFT provider diagnostic and a subsequently tested
partial-output repair. The latter was **not** used in the retained native runs.

The subsequent [phase-sensitive protocol](QFT-STATE-PROTOCOL.md) ran that capture
variant natively: [70 QFT cases passed](../../evidence/2026-09-12-qft-states/README.md),
and the Decoder timeout retained its first-search-iteration checkpoint. Read the
per-experiment records for exact versions; the earlier timeout remains missing
its partial output. Full Decoder still has no successful result observation.

The [trace-only follow-up](SEARCH-TRACE-PROTOCOL.md) now
[locates the timeout inside 18-control Z expansion](../../evidence/2026-09-12-search-trace/README.md).
Current guest code builds the hash-bound traced source; removing the marked
insertions reproduces the original Core source. It is diagnostic code only.

From the independent Qristal checkout:

```sh
python3 -B qualification/full_decoder/cloud/pack.py NEW_ARTIFACT_DIRECTORY
python3 -B qualification/full_decoder/cloud/run.py NEW_ARTIFACT_DIRECTORY NEW_RUN_DIRECTORY
```

Packing requires the explicitly named public build/install caches from the
previous community build. It creates a manifest of source hashes and revisions,
then a checksum for the archive. It neither rebuilds nor modifies those caches.
The native experiment reuses installed dependencies; it is not a fresh build of
all dependencies from upstream source. Existing absolute plugin links are
preserved only after validating their mapped `/work/install-core/lib` targets.

Running uses the operator's existing AWS CLI authentication. It creates one
private transfer bucket, one dedicated group with no inbound rules, and one
2-vCPU/8-GiB VM. Guest build/test processes run as `ubuntu` in a network namespace
without network access. The guest receives no IAM instance profile. Toolchain
installation happens separately as root using public Ubuntu packages.

The VM supervisor immediately records exact instance/disk/group identities and
uses a fixed client token for ambiguous launch recovery. Its 20-minute budget
includes boot, installation, compilation and execution; cleanup has another
five minutes. The guest also schedules instance-terminating shutdown. No observed
failure justifies silently extending either deadline or replacing the instance.

The runner returns success when a checksummed report was recovered and resources
were cleaned. **That is not a test-pass verdict.** Read the recovered report:

- Bootstrap failure: no native test conclusion.
- Build failure: retain compiler diagnostics; subsequent stages did not run.
- Six initialization tests: each named case and the six-test total must pass.
- Tiny fixture timeout/failure: no full-algorithm qualification.
- Explicit no-improvement: caller-contract execution only, inconclusive search.
- Oracle-consistent candidate: one small observation, not full correctness.

The rebuilt Core library's file hash is recorded. This first VM protocol does
not independently capture its loaded-library mapping. Decoder is compiled into
the test programs directly. Consequently, neither a successful stage nor a full
run permits an installed-plugin or runtime-source-lock promotion.

`transfer.json` retains exact transfer identity and cleanup status. `vm/` retains
only filtered checksummed console records, resource IDs and supervisor status;
no raw console, signed URL or bootstrap script is retained. Report log tails are
bounded; full guest compiler/runtime logs disappear with the VM. This limits
diagnosis and must be stated when interpreting missing output.

If execution is interrupted, use the existing supervisor's `cleanup` action with
`--directory NEW_RUN_DIRECTORY/vm` within the original deadline. Transfer cleanup
is independent: use only the exact account/bucket/key in `transfer.json`, verify
ownership, delete that object and bucket, and require an absent-bucket response.
Do not infer successful cleanup from a stopped observer.

Offline lifecycle tests inject failures before launch, during launch/observation,
and during VM cleanup. They verify that transfer cleanup still runs and that
signed URLs do not enter retained records. They launch no AWS resources.
