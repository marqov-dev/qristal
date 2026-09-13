# Fresh XACC build and installed consumer passed

On 13 September 2026, one new bounded m7i.large CPU VM built XACC from
hash-verified Git-object exports and three explicit patches. The ANTLR output
patch corrected the first attempt's source/dist write; source mounts remained
read-only. No historical installed prefix or QB binary image was an input.

All nine stages passed: toolchain 84.19 seconds, inventory 5.73, offline configure
25.72, offline compilation 431.00, build tests 0.16, installation 0.67, separate
consumer compilation 1.77, linkage 0.16 and installed tests 0.26. Both test runs
passed the same four phase-sensitive ACZ fixtures and one Bell fixture: five
distinct fixtures, not ten. Bell counts were 485/539 in the build and 540/484 in
the installed run. Installed consumer compilation/execution had no build/source
mounts. Workload containers were non-root, network-disabled and resource-bounded.

The public toolchain reported GCC 11.4.0, CMake 3.22.1 and Python 3.10.12. Its base
was digest-selected, but apt resolution was live; the package inventory is only
partially retained with a full-log hash. This is not bit-reproducible toolchain
proof. Configure warned that Qiskit was absent and skipped the Python API; no Aer
pulse, Python API, Core or GPU runtime qualification follows from this run.

The first independent verification rejected a truncated linkage tail. The saved
800-character head and 2200-character tail overlap by 130 characters; their
2870-byte reconstruction matches the original full-log SHA-256 exactly. The
checker now requires that full-hash match before inspecting the complete linkage
text, retained separately here. Missing middle bytes or changed hashes fail
closed. No native rerun, output fabrication or relaxed linkage check was needed.

`verification.json` records the narrow passing classification. `input-identity.json`
binds the native guest/runner revision, archive and compressed effective manifest.
`result.json` retains exact commands, exits, timing, bounded logs and library
hashes. The installed manifest covers 3525 regular files but only its hash/count
and selected library hashes were transferred: the complete installation and full
compiler logs were destroyed with the disposable VM, as predeclared.

All started workload containers were removed. Exact VM termination, one root disk,
security group and private transfer cleanup were verified. Public cleanup records
omit infrastructure identifiers; original operator receipts remain local.
The earlier failure remains in `../2026-09-13-xacc-source-build`.

Next: retain a reusable fresh XACC installation with its full receipt, then build
Core from the separately reconstructed inputs in
`../2026-09-13-core-source-inputs`. Core needs explicit Eigen build-directory
staging and complete separate Python artifact sets. This experiment does not
publish/promote a runtime or complete hosted Marqov admission or full Decoder.
