# Exact-package multipart transport

`multipart_transport.py` is an optional operator-only fallback for the approved
314,255,079-byte Core archive after two single-request uploads reached their
600-second limit before VM launch. It does not change the archive, guest,
fixtures, native stages, or existing protocol-bound operator files.

Run it with the same prepared-artifact and new-state-directory arguments as
`run.py`. It rejects any other archive identity and records its own source hash
in `multipart-transport.json`. The unchanged runner still checks the original
protocol identities before resource creation.

The upload uses two workers with 8 MiB parts and a fixed 3,600-second subprocess
limit. Its prior 600-second attempt completed 15 of 38 parts before timing out;
the exact multipart upload was aborted, absence verified and the empty bucket
deleted without launching a VM. The executed wrapper and tests are preserved in
`../evidence/2026-09-13-core-prelaunch-timeout/multipart-operator/`, with the
executed wrapper hash
`8bb646abedb7fc6d0d5b721e9ebfd7b5dfe3bfc223f6562dd8874d97c81b94fb`.
This revised prelaunch transfer allowance does not extend the native observation
or cleanup deadlines and changes no approved archive bytes.
The upload ID is persisted before parts start. Each returned part checksum is
checked, and the local archive is hashed before and after upload. HEAD checks
object size, metadata and encryption; it does not independently establish a
remote whole-file SHA. The unchanged guest archive SHA check is authoritative
before native execution.

A failed upload gets a separate, at-most-90-second abort attempt targeting only
the persisted upload ID. Cleanup requires `s3:AbortMultipartUpload` and
`s3:ListMultipartUploadParts` in addition to normal object permissions. Missing
upload identity, denied cleanup or uncertain object completion remains explicit
recovery state. The wrapper does not guess IDs or delete an uncertain object.
An exact temporary bucket may therefore require follow-up recovery even when
no VM launched.

Ten offline tests cover identity rejection, checked/ordered parts, timeouts,
redacted permission failures, missing upload identity, wrong checksums and lost
completion responses. These tests establish operator behavior, not AWS success
or native Core qualification. Native observations belong in the evidence index
once the run has returned and cleanup is verified.
