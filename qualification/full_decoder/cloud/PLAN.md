# Independent CPU VM qualification — predeclared

Purpose: unblock native Decoder investigation without consuming shared Docker.
Existing AWS authentication and a RunInstances dry-run for m7i.large succeeded.
AWS reports 2 vCPUs and 8192 MiB for this type. No instance was created by dry-run.

One Ubuntu 22.04 m7i.large, 20-GiB encrypted/delete-on-termination root disk,
dedicated tagged security group with no inbound rules, no IAM instance profile.
A private transfer bucket/object uses a short-lived read URL; no signed URL or
bootstrap credentials enter retained evidence. Public-access blocking is enabled.

Supervisor observation limit: 1200 seconds; cleanup: 300 seconds. Guest schedules
shutdown/termination after 20 minutes as a backstop. The existing supervisor binds
account, client token, instance, exact root volume and dedicated group. Both VM
resources and the transfer object/bucket must be cleaned and verified.

Artifact: only public installed Core/XACC prefixes, explicit source/test paths,
cached GoogleTest headers/libraries and generated plugin registration sources.
Links must resolve inside the independent QB workspace, except the existing
/work/install-core/lib plugin links: preserve those exact guest-prefix links only
after validating that their host counterparts exist in the packaged Core prefix. Preserve
local installed prefixes. Retain archive SHA-256, input hashes and merged SHAs.

Guest bootstraps the existing public Ubuntu toolchain recipe, then builds in its
own output directory. Build stages are capped at 180 seconds; runtime stages at
60 seconds. Each stage runs as ubuntu, without networking, with 4-GiB address-space,
256-process and CPU limits. This is a disposable VM experiment, not proof of the
platform's managed-runtime isolation policy or a rebuilt distribution image.

First rebuild only the Core search plugin and overlay it inside the disposable
VM. Compile/run the six current Decoder initialization tests, then compile/run
the direct-source 24-qubit caller-result consumer. Decoder itself is linked into
the test executables; this is not installed Decoder-plugin qualification.
No-improvement remains inconclusive. Timeout/failed stage is retained; no retry
or time-limit extension after results. Only bounded checksummed result chunks
are recovered from console; unrelated bootstrap output is discarded.
