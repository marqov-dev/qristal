# Frozen native QPP image experiment — completed

Prepared from main `25559c95220e3e49e3ec1c75346658cd95bc3591` (PR49).
The authorized experiment subsequently passed all nine native checks and independent
cleanup verification. See `../evidence/2026-09-14-native-image-success`. The frozen
protocol and command below are retained as historical execution inputs; do not
launch a duplicate run. Hosted admission and redistribution remain separate.

The image is unchanged from PR49: OCI index
`sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f`,
config `sha256:0127d58acfa19aae8fe4ab911b1acbb9993d8ab16ebd40ad55421480457907f0`.
The inner native protocol SHA256 is
`abf2a06335287214ef914d9af4f04d6c12a7df452c8ccaa122e8c706272072be`.
The cloud protocol SHA256 is
`9a77717db1ca8da397e04a05fc99a03944549c10d71af5c5dd6a9414f1871d86`.
The prepared transfer archive is 512,261,555 bytes, SHA256
`cb7510e24ab4e2a6e376c1a3ebcc75cdd29b19845f7369de3c141117430dbfdb`.
This compressed transfer archive is distinct from the saved Docker image archive.

## What the run will do

The wrapper reuses the existing disposable CPU VM supervisor. It creates one
m7i.large in account 090208085542, us-east-1, with a 20 GiB encrypted root disk,
no inbound security-group rules and no workload IAM profile. The observation
window is 3,600 seconds with 300 seconds reserved for cleanup. The guest has a
1,500-second cap. No retry VM or persistent service is included. Private signed
transfer URLs stay out of reports; no credentials enter simulator containers.

Before any resource activity the operator snapshots the transfer inputs, checks
external archive/protocol hashes and the protocol inside the archive, and checks
all frozen operator source hashes. The guest requires Linux x86_64 and an empty
local system Docker daemon, verifies all image archive descriptors/layers before
loading, then checks the loaded runtime configuration and full diff-ID chain.
It accepts the verified index or config identity according to the actual engine's
image lookup behavior; a mutable tag cannot substitute for that identity.

Nine checks follow: the existing six QPP capability/circuit/rejection cases,
five imports in one case, and separate NumPy and SciPy numerical/loader cases.
All use nonroot, networkless, read-only containers with CPU/memory/PID limits and
exact named-container absence checks. The original six-case local receipt is
retained byte-for-byte; its historical schema/flags are not relabelled. New host
observations and operator EC2 identity checks are separate evidence.

A bounded JSON envelope preserves raw execution/probe files and their protocol.
The guest uploads it privately and emits a compact checksummed console reference.
The operator checks the downloaded bytes, protocol, image identities, all cases
and cleanup claims, then records the exact EC2 architecture/type/AMI/subnet/VPC/
client-token/tag binding. Only verified, durably retained evidence permits output
object deletion. Failed verification keeps the private recovery bucket; VM cleanup
still runs. The lifecycle separately verifies VM/volume/group/bucket cleanup.
Neither the guest nor its evidence classifier certifies resource cleanup itself.

## Execution interface

The existing operator environment has boto3/botocore 1.35.99. No dependencies were
installed for preparation. The AWS CLI and host Docker package remain external
operator/bootstrap dependencies; Docker's version is not pinned by this bundle.
Read-only preflight confirmed the expected account and available Canonical amd64
Ubuntu AMI `ami-05a3e9423ae4d7a19`; this is not a capacity or launch guarantee.

After the separate one-run authorization, use the exact reviewed checkout:

```sh
/private/tmp/qb-artifact-operator-20260913/bin/python -B qualification/core_package/native_image_cloud.py run \
  '/Users/david/Marqov Artifacts/qristal/native-image-cloud-2026-09-14' \
  /private/tmp/qpp-native-image-run-20260914 \
  --archive-sha256 cb7510e24ab4e2a6e376c1a3ebcc75cdd29b19845f7369de3c141117430dbfdb \
  --protocol-sha256 9a77717db1ca8da397e04a05fc99a03944549c10d71af5c5dd6a9414f1871d86
```

The state directory must be new. Keep it private: it contains exact resource IDs
and recovery coordinates. Do not run on an existing shared Docker host. Existing
local images, platform services, SDK/compiler work and GPU infrastructure are
outside this experiment. A source change requires a newly frozen package.

Preparation passed 501 offline tests across 27 suites, including mocked retention
success/failure ordering. Those tests do not prove AWS behavior. Keep the prior
three standalone library findings and original source console-recovery limitation.
Public distribution coverage and managed-execution admission remain separate.
The main agent was observed active and was not messaged or interrupted.
