# Fresh XACC build with retained installation

The user explicitly approved this single temporary CPU run in AWS account
`090208085542`, `us-east-1`. The source-build input archive is unchanged from the
previous successful out-of-tree experiment; its identity is retained here.
The wrapper implementation was merged in PR38; Core preparation commit `20bc27b`
adds no change to the native guest or wrapper.

## Results

All nine native stages exited zero. Configure took 25.87 seconds, compile 409.16
seconds, and the separate installed-only consumer compile took 1.62 seconds.
Four phase-sensitive ACZ fixtures plus one Bell fixture passed both in the build
and through the installed consumer. These are five distinct fixtures, not ten.

The 17,059,046-byte downloaded archive contains the full installation (3,525
regular installed files), consumer source/binary, and all nine complete stage
logs. SHA256:
`b4569c7ca587c3a1fcbaa5e87a4606792c9a0904e2d15c5c2ef03a83b3088bb5`.

The operator verified hashes, file modes and relative links, installation and
consumer identities, and full-log/report bindings before deleting the transfer
bucket. A second local CLI verification passed after cleanup. Archive members
were neither extracted nor executed by these verifiers. The full archive remains
at `/private/tmp/qb-xacc-retained-run-20260913/output.tar.gz`; it is intentionally
not committed as a binary or published as a supported runtime.

`retention.json` contains an unchanged nested native classifier result with
`complete_install_artifact_retained: false`: that classifier measures the
original guest only. The wrapper's top-level `verified: true` plus the bound
archive SHA establish the newly completed retention step. Do not interpret the
nested field as the overall retention outcome.

## Cleanup and remaining scope

`cleanup.json` and `resources.json` verify termination/deletion of the exact VM,
root disk, security group and private transfer bucket, with no cleanup errors.
No signed URLs or credentials are retained in this evidence.

This establishes a freshly built, verified installed artifact at its original
`/work/install-xacc` prefix. It does not establish relocatability or replay after
extraction onto another host. Core configure/build against this installation,
complete native Python dependency setup, final runtime distribution and hosted
admission remain separate gates. Full Decoder remains off the critical path.
