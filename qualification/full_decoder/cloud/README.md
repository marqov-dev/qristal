# Independent CPU VM probe

This is an operator-owned native experiment, separate from hosted execution and
the shared local Docker environment. Read [the predeclared plan](PLAN.md) first.
The runner has fixed account, region, AMI, subnet, instance type and deadlines;
it is deliberately not a general provisioning interface.

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
