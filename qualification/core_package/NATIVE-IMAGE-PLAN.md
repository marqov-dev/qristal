# Next native image qualification: proposal only

The exact private archive is 514,063,872 bytes, SHA256
139d7b3e5bc463f2067bfd9a5beda4a59326a996d7fd8d95ea9e3f06c332a4eb.
Its OCI index is sha256:8d8a81d995325ae9c452dca2698442b02c735cc6eae9d98ea78a38532a5a8266.
Any notice overlay or runtime change creates a new image identity and must be
separately bound and tested; these values cannot silently carry over.

Prepare one bounded native runner using the existing independent QB experiment
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
