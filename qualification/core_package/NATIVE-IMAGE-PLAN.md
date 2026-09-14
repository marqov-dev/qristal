# Native image qualification: bounded run completed

The notice-overlay image passed the authorized native AMD64 replay and independent
cleanup verification; see `../evidence/2026-09-14-native-image-success`. The next
boundaries are distribution coverage and managed-execution admission.

The tested candidate is the notice-overlay image, OCI index
`sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f`.
Its private archive is 514,349,056 bytes, SHA256
`451b0710cea596fcae3bf717caed723ab18677cab0e3354b11c3db9761a96ab5`.
The saved archive preserves the ten baseline layers and complete runtime config,
adds only 142 attribution payload files, and passes six local emulation probes.
See `../evidence/2026-09-14-attribution-overlay`. This replaces the proposed
candidate identity, not the historical evidence or remaining native/hosted gates.
Full distribution coverage is still incomplete.

The earlier baseline private archive is 514,063,872 bytes, SHA256
139d7b3e5bc463f2067bfd9a5beda4a59326a996d7fd8d95ea9e3f06c332a4eb.
Its OCI index is sha256:8d8a81d995325ae9c452dca2698442b02c735cc6eae9d98ea78a38532a5a8266.
Any notice overlay or runtime change creates a new image identity and must be
separately bound and tested; these values cannot silently carry over.

The bounded runner is now frozen in `NATIVE-IMAGE-RUN.md`, including the existing
independent QB experiment supervisor and verified private result retention.
The following resource proposal is historical; its single authorized run completed.
Do not relaunch it implicitly. It used the existing QB experiment
supervisor, with one m7i.large in the previously approved account/region, encrypted
20GiB root disk, no inbound ports or workload IAM profile, and private transfer
objects. Keep upload preparation separate from the 3,600-second VM observation
window and reserve cleanup time. No retry VM or persistent service is implied.
This document does not launch or authorize that experiment.

Before launch, freeze the exact image archive, verifier, loader/probe scripts and
protocol. Verify the archive and all descriptors on the native host before load.
Record physical execution architecture separately from requested container
platform, image index/manifest/config identities and every command/result.
Run QPP identity/Bell/asymmetric bit-order cases, capability and rejection checks,
imports and numerical operations under the existing nonroot, networkless,
read-only, CPU/memory/PID limits. Do not relabel the existing local-emulation
probe receipt as native evidence; the runner needs a distinct native-host record.

Retain bounded reports and complete failure logs, verify artifact hashes before
transfer deletion, and independently verify exact VM/volume/security-group/bucket
cleanup. The current three standalone wheel-library ldd findings must remain in
the evidence alongside installed-loader results. They are not an excuse to alter
library search paths globally or suppress arbitrary missing dependencies.

Hosted admission remains a separate managed-execution owner decision about the
exact image/profile and execution contract. Native VM success alone does not wire
the local CLI into hosted Projects/Reports. No production deployment or GPU work
belongs in this bounded CPU image experiment. Full Decoder stays off the path.
