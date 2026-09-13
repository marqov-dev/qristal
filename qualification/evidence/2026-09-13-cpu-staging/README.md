# CPU input staging, 13 September 2026

Captured the existing isolated installed-runtime workspace and staged an explicit
OCI context locally. `observation.json` retains the context record/hash and final
validator hash. The large installed binaries/context remain local at
`/private/tmp/qb-cpu-context-20260913`; they are not published by this record.

The real-input preflight initially rejected absolute XACC plugin links to installed
Core libraries because it tried to resolve Linux `/work` paths on the Mac host.
The corrected validator resolves only declared container files. Existing links
were preserved; installed binary bytes were not rebuilt or patched.

Independent review also found and corrected recursive output copying, private
umask parent permissions, destination-symlink following during the Bell overlay,
and invalid parent-traversal links. Fifteen fixture tests cover successful staging
and rejection cases. Final context verification passed against the real payload.
No Docker invocation, apt acquisition, native runtime test, registry change or
platform change occurred.

This proves local staging/consistency only. It does not reconstruct missing build
provenance, prove runtime compatibility, or establish an available CPU release.
The next native experiment is the clean OCI build plus existing ten image test
groups against its exact identity. Apt availability and the new assembled runtime
remain unverified. The old qualified CPU artifact remains the catalog entry.
