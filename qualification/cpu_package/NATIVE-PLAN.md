# CPU OCI native experiment — 13 September 2026

Baseline: merged PR34, f640543825475d3d94c508290135d8bbba095cc3.
Use the already checked context from the retained CPU staging observation.
Rebuild the image assembly only; reuse installed binary inputs without claiming
fresh compilation or restored build provenance.

Reuse the existing fixed CPU VM lifecycle: one m7i.large in us-east-1, Ubuntu22.04,
20GiB encrypted/delete-on-termination root disk, no inbound rules or IAM profile,
private checksum-bound archive transfer. No shared Docker or platform changes.
Total observation deadline1200seconds plus300seconds cleanup, with20minute guest
shutdown. Exact instance, root disk, security group and transfer bucket cleanup
must be verified. No retry or deadline increase after results.

Transfer timeout120seconds; Docker installation240seconds; image build480seconds;
image test harness240seconds. The global VM deadline overrides stage budgets.
Docker build memory4GiB and CPUquota2; the nproc ulimit is not a cgroup PID limit
for root build steps. Test containers use existing2CPU/4GiB/256PID limits,
no network or mounts, read-only roots and dropped capabilities. An outer timeout
can leave Docker activity until whole-VM cleanup; do not claim immediate cleanup.

Preflight validates context inventory and named harness hashes before any build.
Build uses the digest-pinned CPU Dockerfile and existing apt list; dependency
availability and apt resolution remain experimental. Record Docker version,
image/configuration identity, build/check output tails and hashes, all ten test
groups and individual log tails. The fixed test harness covers43 functional
fixtures plus CLI/negative/isolation checks. The reported test image must equal
the built and inspected ID. A recovered report is not itself a native pass.

Retain failures, source/context/archive hashes and cleanup evidence, sanitizing
infrastructure identifiers before repository publication. Raw bootstrap, signed
URLs and operator credentials must not enter evidence. No registry publication,
new runtime catalog entry or hosted admission follows automatically from this run.
