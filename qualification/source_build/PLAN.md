# Fresh XACC/QPP experiment

Baseline: merged PR37, `8d1258cd5f21c85163bc832ada097e83bef9f6ed`.
Use only the retained pristine-source exports, checksum-verified Boost archive,
two named compatibility patches and ACZ fixture. Apply patches to a new copy,
retain their hashes and the complete effective input inventory, then pack once.
Do not reset, clean or mount the existing research build/install directories.

One fixed m7i.large CPU VM, 20 GiB encrypted/delete-on-termination root, private
transfer bucket and dedicated no-inbound security group, using the existing fixed
CPU lifecycle. No IAM instance profile or shared Docker. Observation ceiling is
3600 seconds, cleanup 300 seconds; guest shutdown is scheduled for 60 minutes.
This replaces the earlier proposed 60-minute *compile* allowance with a tighter
900-second compilation bound inside a one-hour total ceiling before execution.
No automatic second launch or deadline extension after a result.

Install Docker on the disposable host, then build the public digest-based Ubuntu
toolchain with the captured recipe (600 seconds). Record its resulting image
identity. Apt resolution remains live and is inventoried, not snapshot-reproduced.
Only toolchain acquisition is networked. Subsequent named containers have no
network, UID65532, read-only root/source inputs, two CPUs, 4 GiB memory including
swap, 256 PIDs and no capabilities. Only fresh build/install roots and tmpfs are
writable. Configure: 300 seconds; build: 900; install: 120; tests: 60 each.

Run the existing four phase-sensitive ACZ circuits and Bell check from the build,
then compile a separate consumer against installed headers and libraries (120
seconds), with an explicit installed-prefix RPATH. Its compilation, linkage check
and execution have no source/build mounts. Both runs must
succeed; retain failures without reducing the test scope. Record stage command,
exit/time, bounded log tails and hashes, builder ID, effective source manifest
hash and installed-library hashes. The full installed-file inventory is hashed
but not transferred in this first bounded console protocol; consequently this is
not yet a complete reusable source-to-install artifact release. No installed
archive or image is published by the experiment.

The console report is checksummed and bounded by the existing decoder. Full
compiler logs and installed files disappear with the VM. A recovered report is
not itself a pass: `native_passed` must be true and all stages must exit zero,
with containers removed. VM, exact disk/group and transfer cleanup are separately
verified. No claim of CPU candidate promotion, all-simulator reconstruction,
full Decoder qualification, or hosted platform admission follows from this run.

Transfer-only attempt 1 hit the default 90-second PutObject timeout. No VM or
security group was created; private transfer cleanup passed. Attempt 2 sets an
explicit 300-second upload bound before launch. Guest/compilation/observation
bounds remain unchanged. This is a new recorded transfer attempt, not a deadline
extension of a running VM or a second native launch.

## Second native protocol, after the first VM was cleaned

The first VM built its public toolchain (86.24 s) and configured offline (24.52 s),
but compilation failed after 10.10 s when ANTLR created a source-tree dist directory.
No build/runtime/install pass was obtained. Exact VM/disk/group and transfer
cleanup passed. The new xacc-build-output.patch moves the ANTLR output and all
eight CMake files referencing source/dist into CMAKE_BINARY_DIR/dist. It changes
output placement only; source mounts stay read-only. The patch is recorded as a
third named transformation. A new input archive and new native attempt use the
same 3600/300-second lifecycle and per-stage limits. Stage heads are retained as
well as tails to preserve compiler version output. This is an explicitly revised
experiment, not an automatic replacement or extension of the original VM.
