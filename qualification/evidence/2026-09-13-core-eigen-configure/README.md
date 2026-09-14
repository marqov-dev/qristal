# Core repeat: Eigen configuration blockers

The approved repeat used the path-guard package after PR43 merged at
`e5bb9aa9ba609935412671ca9ca8674276a61475`. Its input archive was
`52c90c0db488806109d381410d23978e973b32446c2e080780f9aba666659650`
(314,255,620 bytes).

**Core configuration still failed; compilation and installed consumers were not
reached.** The prior eleven missing-argument macro errors are absent, establishing
that the path-guard correction worked in the native environment. Public builder,
material verification/staging, XACC replay, offline ANTLR wheel build and Python
installation with `pip check` passed again.

Two connected failures remain:

- Core's nested Eigen configuration did not produce `cmake_install.cmake`; the
  following install/config include failed. The old command relied on a working
  directory it did not explicitly create and ignored its result. The logs establish the missing
  output, while the working-directory explanation comes from source inspection.
- Our global `CMAKE_DISABLE_FIND_PACKAGE_Eigen3` setting blocks autodiff's
  legitimate `find_package(Eigen3 REQUIRED)`. Those global settings were too broad.

The follow-up fixes the flow together: explicit CPM source overrides bypass only
Core's own optional ambient lookup; nested dependency lookup stays available.
All eleven actual CPM source/binary selections remain mandatory audit inputs.
Eigen uses explicit `-S`/`-B`, fails immediately on configure/install errors, and
keeps its nested build directory for diagnosis. This is a preparation change,
not evidence that the corrected flow has run natively.

## Evidence and cleanup

The complete eight-stage logs, report and receipt are retained in
`output.tar.gz`, SHA256
`77425079e855f3977febee29d47f9b792a2b720a0d350970a193ca272d5d79a5`
(36,974 bytes). Original report/protocol and exact transport operator are retained;
resource metadata uses aliases. No credentials or signed upload requests are
included.

The runner verified VM and storage cleanup. Independent AWS reads confirmed the
instance terminated or absent, and disks, security group and bucket absent. The
first independent check assumed a nonempty terminated-instance record; AWS
returned no reservations, so the subsequent check explicitly accepted absence.
See `independent-cleanup.json`. No resources remain and no further VM launched.

This run does not establish missing public source, an XACC failure or Python
incompatibility. It also does not qualify a new Core runtime or hosted backend.
Keep the earlier failure and this result separate when describing progress.
