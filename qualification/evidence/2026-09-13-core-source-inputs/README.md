# Core input reconstruction — no native Core build

While the revised XACC experiment ran independently, locked Core commit
`a5c3e5fa544c07d538974d3a289b19652d483848` and all eleven C++ dependency commits in
`2026-09-09-installed/core-dependency-lock.json` were exported from local public Git
objects into new directories and verified against complete per-file receipts.
The output root is `/private/tmp/qb-core-pristine-source-20260913`; no research
checkout, dependency cache, installed prefix or runtime image was modified.

The compressed receipts and `summary.json` retain commits, tree identities,
per-file hashes and both compressed/original receipt hashes. The cache-directory
keys in the dependency map are CPM cache keys, not commit IDs. Dependencies were
exported at the recorded commits, not their current working-tree contents. The
Core and XACC GoogleTest pins differ intentionally; do not silently unify them.

The pinned CPM 0.36.0 script and Eigen patch were copied and hashed, along with
separate Core Python constraints and Integrations requirements. **No Python
artifacts were downloaded or installed.** Those files constrain versions but do
not yet provide a checksum-locked Linux/Python3.10 wheelhouse or complete build
requirements. This is source availability/identity evidence, not upstream
publisher authentication or compilation evidence.

An explicit Git ancestry check confirms historical Core Eigen installation fix
`d393cf0e118ffa631e61f36148a41c028685ddea` is an ancestor of the selected Core
revision. That clarifies source history; it does not prove which historical
installed binaries contain it. The selected Core `cmake/dependencies.cmake`
still stages Eigen under `${CMAKE_CURRENT_SOURCE_DIR}/deps/eigen3`. A recorded
build-directory relocation is needed before compiling with read-only source
mounts. Its exported Eigen install paths must also be checked.

Next materials/gates: usable fresh XACC installation plus its receipt; explicit
Core Eigen staging transformation; the complete separate Core/Qiskit0.46 and
Integrations/Qiskit1.2 artifact sets; offline dependency selection with no
configure-time pip upgrades; then native Core/installed-only tests. None of those
remaining gates is satisfied by these source receipts. Existing CPU/GPU runtime
qualification and full Decoder research remain separate.
