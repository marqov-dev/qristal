# Verified Core dependency source preparation — 2026-09-13

All eleven locked dependency exports passed the existing source-provenance
verifier before and after copying. The exact captured Eigen patch was applied
to the derived Eigen copy; exactly four files changed. Every effective source
tree then passed exhaustive manifest verification. The original pristine
sources were not modified. CPM 0.36.0 and the patch were bound to the material
hashes in the checked-in dependency lock.

`preparation.json` records source commits, pristine receipt hashes, effective
manifest hashes, patch before/after hashes, and material identities.
`overrides.cmake` is the generated relocatable cache input.
`verification.json` binds these compact retained files and records seven passing
offline fixture tests. Large effective manifests and source copies remain local.

This is a source-preparation result, not a Core configure/build or native
simulator result. System `find_package` bypasses and nested acquisition remain
subject to actual configure-path validation and a disabled-network native gate.
No change to an existing binary provenance, public availability, or hosted
execution qualification is claimed.
