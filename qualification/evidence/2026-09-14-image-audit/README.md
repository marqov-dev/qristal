# Saved QPP archive and installed-image audit

PR47 merged at `9f6e5d108f771e14fcce3705c11cd1b07a007651`. These checks use the
unchanged private image built in that batch. No runtime image, shared platform
checkout or cloud resource was changed.

## Archive integrity and replay

The saved 514,063,872-byte image archive matches SHA256
`139d7b3e5bc463f2067bfd9a5beda4a59326a996d7fd8d95ea9e3f06c332a4eb`.
Independent verification covers all 16 referenced blobs and all 10 layer hashes
and uncompressed diff IDs (1,260,640,256 expanded bytes). OCI index, amd64 manifest
and config identities are recorded separately: index `8d8a81...`, manifest
`358618...`, config `1d6c425...`. The index includes a BuildKit attestation;
verifying its bytes does not verify the truth of its claims.

The verified archive loaded into the existing local daemon and the same six
bounded QPP CLI probes passed again with exact container cleanup. This is useful
archive/import replay evidence, but it is **not a clean-daemon or native hardware
replay**. Blob/layer verification does not implement a final filesystem union.

## ELF and installed numerical loading

The executed audit inspected 1,065 ELF files in the declared runtime/standard OS
roots, with zero scan errors in 80.09 seconds. All five imports passed: Core,
NumPy, SciPy linear algebra, SymEngine and Qiskit. The full original receipt is
retained in `full-elf-audit.json.gz` and its hash in `summary.json`.

Three individual bundled libraries have unresolved standalone `ldd` references:
NumPy's OpenBLAS and libgfortran, and an unpatched libgfortran copy in scipy.libs.
The original all-standalone-linkage result remains **false**. No global
LD_LIBRARY_PATH override, extra system package or library deletion was applied.

Separate fresh-process NumPy and SciPy probes passed matrix multiplication,
linear solves and SVD reconstruction. Live `/proc/self/maps` records and file
hashes show the installed private BLAS/Fortran/quadmath libraries actually loaded.
SciPy uses its patched library names; reachability of the older unpatched copy
is not established by these probes. These operations exercise the installed
loader paths, not every possible plugin or direct-library invocation.

This interpretation is consistent with auditwheel's documented practice of
bundling libraries and adjusting extension RPATHs, and its warning that static
DT_NEEDED inspection does not capture every dynamic load:
https://github.com/pypa/auditwheel#overview
https://github.com/pypa/auditwheel#limitations

Future audit code now explicitly fails incomplete/deadline-truncated scans.
Future SciPy mapping checks require SciPy's own mapped library family, rather
than accepting NumPy mappings alone; both retained mapping records pass that
stricter offline replay. Exact originally executed guest/driver files are retained
separately, so these later checker changes are not misrepresented as executed.

## Notice reconciliation

A private supplemental bundle contains 35 exact-source notices: Core LICENSE,
30 dependency notice files and four XACC/QPP files. Hashes tie them to executed
material/source manifests. PLY contains embedded redistribution text, narrowing
the previous standalone-filename scan gap. Full coverage remains incomplete.

Public exact-release attribution candidates were also found:

- ANTLR 4.9.2 LICENSE.txt at commit
  `5e5b6d35b4183fd330102c40947b95c4b5c6abb5`:
  https://github.com/antlr/antlr4/blob/5e5b6d35b4183fd330102c40947b95c4b5c6abb5/LICENSE.txt
  The retained sdist's setup.py exactly matches that release source.
- OpenPulse v1.0.1 LICENSE at commit
  `db7bf66e64be290b1d1485652d1c7e92ce07e499`:
  https://github.com/openqasm/openpulse-python/blob/db7bf66e64be290b1d1485652d1c7e92ce07e499/LICENSE
  Its packaging metadata references filenames absent from the package subdirectory,
  consistent with an omission. This is not proof of the wheel's build provenance.

`upstream-report.json` and its acquisition inventory retain exact commit/blob and
SHA256 identities. These are attribution candidates, not a blanket grant or
redistribution clearance. Private bundles are retained separately from the image;
no notice overlay has yet changed the tested image identity.

## Remaining gates

Reconcile and package complete attribution/source obligations, decide treatment
of residual bundled-library reachability, perform native amd64 image qualification,
and coordinate exact hosted image/profile admission. Current results remain local
amd64 emulation. The main release task was inspected read-only; it supplied no new
admission decision, and no acceptance is inferred. Decoder remains off this path.
