# Fresh XACC output retention protocol

This wrapper preserves the qualified `source_build` guest byte-for-byte. It adds
an external emit hook after workload containers have been removed. The first native run passed; see
`../evidence/2026-09-13-xacc-retained-install/README.md` for its exact scope. It does not publish a
runtime or establish portability of its absolute `/work/install-xacc` paths.

Run with an existing prepared source-build artifact and a new operator state
directory: `python3 -B qualification/source_artifact/run.py ARTIFACT STATE`.
The operator Python 3.10+ must already provide boto3; exact operator-only wheels
are pinned in `requirements-operator.txt` for `pip --require-hashes
--only-binary=:all:` in an isolated environment. Wheel hashes and dependencies
were read from PyPI version metadata; this implementation installed no packages.
This command installs nothing on
the operator host. The underlying fixed disposable guest installs its existing
toolchain as in source_build. No shared Docker daemon is involved.

## Fixed bounds and isolation

- One existing fixed m7i.large VM, 2 vCPU, 8 GiB RAM, encrypted 20 GiB root;
  no inbound rules or IAM instance profile. Same non-root, networkless,
  read-only-source build and consumer container commands and stage bounds.
- 3,600-second observation, 300-second cleanup, 60-minute guest shutdown.
  Artifact upload adds at most 315 seconds inside that observation budget.
- One additional private object, `source-output.tar.gz`; PUT-only presigned URL
  expires after 3,900 seconds, requires AES256 and exact expected bucket owner.
  Operator credentials never enter workload containers. URL exists only in
  launch user data and a 0600 guest-host curl configuration; never logged or
  included in the retained archive, and removed after upload attempt.
- At most 1 GiB compressed and expanded archive, 50,000 members, 300-second curl
  upload bound. All operator retention work (native classification, get-object,
  download, fsync and archive verification) has a Unix main-thread signal timer
  bounded by the lesser of 300 seconds and the original observation deadline.
  It receives no new observation budget and preserves the cleanup window. With
  under one second remaining it fails before making a download request.
- EC2 user data checked against its 16 KiB limit before launching.

## Retained evidence

Archive contains installed XACC, consumer source/binary, full logs for every
recorded native stage, the original native report and an exhaustive receipt.
Regular files bind mode, length and SHA256; directories bind mode; symbolic
links bind mode and relative target. Special files, hardlinks, unsafe paths,
escaping links, duplicate members and children beneath non-directories fail.
The verifier streams tar contents without extracting paths or executing them.

Console evidence adds archive hash/length and receipt/report hashes. Operator
first runs the unchanged native report classifier, downloads while the bucket
exists, independently verifies all receipts and report/log/install/consumer
bindings, and writes `retention.json` before cleanup. Recovered failure is not
native success. Download creates a new local file and never overwrites one.
The archive and parent directory are fsynced before retention is marked verified
and before any output object deletion.

VM cleanup still runs on failed output retrieval. If upload/retrieval/report
recovery is uncertain, the private transfer bucket is intentionally retained;
`transfer.json` preserves its exact identity and records a cleanup error. When
available, `retention.json` additionally records the output key and error class.
No exception containing signed URL data is retained. An operator must recover
and verify the output or explicitly delete this exact temporary bucket; no
automatic retry VM or broad bucket deletion is allowed. Output deletion and
bucket absence are verified by the original lifecycle after successful local
retention. This intentional recovery exception can leave private storage costs.

## Before a native run

Review wrapper changes, run offline tests, confirm installed boto3 and current
AWS identity using normal tools, calculate user-data size with the actual URL,
and retain wrapper hashes plus source-build archive identity. After the run,
retain both native classification and retention verification, exact cleanup
outcome, and full artifact locally. An independently mounted consumer replay
from the downloaded artifact remains a separate qualification; no executable
distribution claim follows merely from archive verification.

The runner writes `wrapper-identity.json` before creating its transfer bucket,
binding five wrapper/dependency files and the fixed output key without retaining
signed URLs. The original transfer receipt binds the input archive.

Boto3 API reference:
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/generate_presigned_url.html
