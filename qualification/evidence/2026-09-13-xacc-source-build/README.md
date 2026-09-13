# First fresh XACC build attempt — source-output failure

At merged qualification baseline `8d1258cd5f21c85163bc832ada097e83bef9f6ed`,
the pristine XACC/GoogleTest sources and verified Boost archive were prepared with
the two existing compatibility patches. The complete effective input inventory
is retained compressed; `input-identity.json` binds it and the archive to the
exact guest (`9b93a11…`) and runner (`d7004ec…`) revisions.

The first transfer timed out after its 90-second allowance before any native
launch. Its bucket was removed and verified; the failure is retained in
`transfer-attempt-1.json`. A new transfer attempt used a 300-second bound,
succeeded, and launched exactly one fixed CPU VM.

| Stage | Result |
| --- | --- |
| Public Ubuntu toolchain construction | Passed, 86.24 seconds; image identity in result.json |
| Offline XACC configuration | Passed, 24.52 seconds |
| Fresh compilation | Failed, exit 2 after 10.10 seconds |
| Build test / installation / installed-only consumer | Not reached |
| Container cleanup | All started compile/configuration containers removed |
| VM, exact root disk, dedicated group, transfer bucket | Cleanup verified |

ANTLR's target attempted to create `/work/xacc/dist`, inside the deliberately
read-only source mount. This is the first observed build blocker, not evidence
that a private QB library is missing or that all further dependencies are proven.
Configuration also reported missing Qiskit for the optional Aer pulse adapter;
this run does not qualify that capability. Full guest logs were hashed, with
bounded tails retained; the package inventory tail is incomplete and earlier
compiler-version output was not retained. No installed artifact or replacement
runtime was produced.

`result.json` retains the native report. `cleanup.json` retains verification
outcomes and exact volume count without publishing cloud identifiers. Original
resource-bound audits remain in the local run directory. The classifier must
report `native_passed:false`; report recovery and cleanup success do not override
the compilation failure.

Next: move ANTLR's output and its CMake consumers into the binary directory using
a separately recorded patch, then repeat under the same resource/stage bounds.
Keep the source mounts read-only. Do not rewrite this failure or promote the
existing CPU candidate's original-binary provenance. Source/build changes remain
independent of the platform/SDK release work.
