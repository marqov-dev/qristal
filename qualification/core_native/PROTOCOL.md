# Bounded native Core experiment

This replaces the prior preparation-only boundary with a concrete runner. It is
**not executed or qualified** until an independently verified native receipt is
retained. Keep packaging and hosted-admission claims separate.

## Exact scope

One m7i.large CPU VM in account 090208085542/us-east-1, encrypted 20 GiB root,
new no-inbound security group in the existing proof VPC; no instance profile.
The existing supervisor enforces a 3,600-second observation and 300-second cleanup
window, plus guest shutdown. No shared platform infrastructure is changed.

Public source/wheels, the previously retained XACC installation and bound scripts
are assembled by `package.py`. Its toolchain uses the same pinned Ubuntu base and
hash-bound public apt recipe as the XACC proof. Apt resolves package versions
inside the fresh builder; the package inventory and builder image identity are
retained. This does not claim bit-reproducible apt resolution.

The guest builds only the toolchain image with network access. Every workload
stage runs as UID65532, with no network, read-only root, dropped capabilities,
no-new-privileges, 2 CPUs, 4 GiB RAM, 256 PIDs and bounded scratch. The public input
mount is read-only. Mutable source/dependency/install derivatives are confined to
the experiment work directory. Individual stage limits share a guest deadline,
reserving time for artifact upload; they do not each receive a fresh hour.

## Gates

Verify frozen inputs; inventory compiler/Python/system packages; stage fresh
copies and replay the retained XACC consumer; build ANTLR and install all hashed
Python wheels offline; configure Core with explicit source selections; check
actual CPM cache paths and original source/install integrity; build explicit
Core/Python/plugin targets; repeat audits; install; normalize only known Core
plugin links; audit the XACC baseline again; compile/run C++ and Python consumers
with original source/build/input mounts absent; check full linkage logs.

The result classifier requires exact indexed stage commands and full archived
logs, not clipped console output. The immutable input receipt remains the XACC
baseline. Core's original files cannot be changed or removed by installation;
only declared, hash-bound plugin links may be added. Normalization precedes
installed-only replay and leaves the reusable XACC archive unchanged.

## Retention and cleanup

A private, run-specific S3 bucket transports one input archive and one output
archive. PUT authorization is held only in a host-side 0600 curl configuration,
never mounted into workloads, printed or archived. Upload requires expected
bucket owner and AES256, and is bounded to 300 seconds. Input upload has a
600-second operator limit before a VM is launched.

Success output contains the two installation roots, ANTLR wheel, consumer and
full stage logs. Failure output contains only named logs and the original report;
if success packaging rejects its scope/links, a separate diagnostic archive is
attempted and the run cannot qualify. No virtualenv, home directory, general
/proof directory, credentials, user data or signed URL enters the output.

The operator downloads, fsyncs and independently verifies the archive before
classification and deletion. Verified diagnostic evidence permits normal cleanup
while returning nonzero native status. Uncertain retrieval preserves the exact
private bucket for recovery; VM cleanup still runs. No retry VM is automatic.
The same existing isolated operator environment and pinned boto3 dependencies
are used; the runner installs nothing on the operator host.

A successful run establishes only installed Core QPP C++/Python identity/Bell
execution in the recorded environment. Aer, other accelerators, full Decoder,
public runtime distribution and hosted execution remain separate gates.
