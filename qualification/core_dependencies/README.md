# Core offline C++ dependency preparation

This prepares source inputs for locked Core
`a5c3e5fa544c07d538974d3a289b19652d483848`. It does not run CMake, install
dependencies, compile, download, launch compute or qualify a runtime.

`lock.json` names all eleven dependency commits from the retained historical
Core dependency lock and binds each verified pristine export receipt. The
preparation helper checks every source before copying, checks the copies again,
and creates effective source manifests. Existing cache/build trees are never
copied. Extra files inside a declared source tree are rejected.

The output includes explicit case-sensitive `CPM_<package>_SOURCE` values for
nlohmann_json, autodiff, cpr, pybind11, **Eigen3**, yamlcpp, range-v3,
cppitertools, googletest, cereal and args. CPM0.36.0 is copied from the
checksum-bound local material into the exact `cache/cpm/CPM_0.36.0.cmake` path
Core's loader expects. `overrides.cmake` is an initial cache input for a later
configure (`cmake -C /path/to/overrides.cmake ...`), not evidence that CMake
actually selected all eleven sources.

## Eigen patch must precede the override

Core's `cmake/dependencies.cmake:85` requests its Eigen patch through
`PATCH_COMMAND`. In captured CPM0.36.0, the manual source-override branch
(lines615–628) recursively calls `CPMAddPackage` with the source directory and
options, **omitting PATCH_COMMAND**. Supplying a pristine Eigen override would
therefore skip the intended patch.

The helper verifies the exact captured patch SHA256, applies it with offline
`git apply` to the verified Eigen copy, and permits changes to exactly its four
declared files. It does not create Git metadata or reuse modified cache bytes.
The final manifest verifies all unchanged files and each patched file; changed
entries drop their original Git-blob identity. Original commits and receipts
remain identified separately. No other source patch is requested by the locked
Core selected CPU dependency declarations; TKET's patch belongs to the disabled
TKET profile.

```sh
python3 -B qualification/core_dependencies/prepare.py /path/to/pristine-core-inputs /new/output
python3 -B -m unittest discover -s qualification/core_dependencies -p 'test_*.py'
```

The helper depends only on Python's standard library and an existing Git command
for patch application. Source/receipt checks run before creating output. A
later patch/copy failure can leave an incomplete directory, but no successful
`preparation.json` is written. Use a new destination for another attempt.

## Remaining gates

- Core's `add_dependency` calls `find_package` **before** CPM. A compatible
  system installation may bypass these overrides. Native configure must record
  and verify actual selected package source/configuration paths and versions;
  this helper deliberately reports `actual_dependency_selection_verified:false`.
- A fresh builder needs the captured CPM script in its expected cache location,
  and writable build/cache outputs. CPM download stamps and dependency configure
  behavior have not been tested against read-only source mounts. Any source
  writes require explicit derived-input handling, not reusing old caches.
- Disable network during configure/build. The overrides are preparation, not a
  network sandbox or a guarantee that no nested package attempts acquisition.
- Reuse the separate [Core source transformations](../core_build/PLAN.md) for
  explicit source version and Eigen staging, then provide retained fresh XACC,
  explicit install/Python output paths and a checksum-locked Python wheelhouse.
  Core Qiskit0.46 and Integrations Qiskit1.2 remain separate environments.
- No Decoder targets are introduced here. Publication and hosted execution use
  separately qualified runtime identities and the platform's existing contract.

This is source preparation. The existing private CPU image's original installed
binary provenance is not retroactively changed.
