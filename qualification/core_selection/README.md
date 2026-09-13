# Core native selection gate (not executed natively)

The first experiment requires all eleven captured C++ dependencies through CPM,
with exact case-sensitive source paths. `check.py` reads **actual**
`CPM_PACKAGE_<name>_SOURCE_DIR:INTERNAL` and corresponding binary-directory
entries written by captured CPM0.36.0 `cpm_store_fetch_properties`, rather than
trusting requested `CPM_<name>_SOURCE` overrides. It rejects omitted/replaced
sources, noncanonical/outside build paths, duplicate cache keys and wrong
Core/XACC prefixes. It is a check of CMake's recorded selection, not proof of
compiled target linkage or a signature over untrusted cache bytes.

Configure must add separate `-DCMAKE_DISABLE_FIND_PACKAGE_<name>:BOOL=TRUE`
options for Eigen3, pybind11, yaml-cpp, GTest, nlohmann_json, range-v3,
autodiff, cereal, args, cpr and cppitertools. These disable Core's preliminary
optional system lookup. Do not carry these flags into the installed consumer:
that consumer needs to find the newly installed exports. System Python, Boost,
OpenSSL, OpenMP, BLAS and CURL remain explicit builder dependencies, not eleven
alternative source selections. Record their versions and actual paths in the
native inventory/configure logs; this checker does not qualify those versions.

Run after configure and again after build, **before Core installation**:

```sh
python3 -B /inputs/tools/qualification/core_selection/check.py /work/build-core/CMakeCache.txt
```

The sibling `core_native/stage_work.py` and `verify_materials.py` must also be
packaged. The parent binds frozen material manifests and cache/log hashes,
runs this gate in a networkless container, records its exit and JSON, and stops
on failure. No build/compiler/cloud commands are executed by this checker.

The source audit reuses the generated-header-only Core guard. All eleven
dependency source trees must remain identical to their captured effective
manifests' materialized copies. Unexpected generated files or changes are
reported as before/after inventory deltas and cause failure; no previously
unknown source mutation is silently accepted. Mutable CPM metadata outside
those source trees is not classified as source provenance. XACC must be exactly
unchanged from the verified extracted installation until Core install; the
separate post-install gate owns allowed new plugin links and targets.

Native CMake behavior remains unverified. A legitimate dependency source write
or nested REQUIRED find-package call affected by the disable flags may require
a narrow documented protocol revision; do not loosen this gate based only on
an expected successful outcome.

Python fixture review: locked Core's `MapVectorBoolInt` manually exposes key
iteration and `__getitem__`, but no `.items()` method
(`src/python/py_stl_containers.cpp:131–187`). Use `result=sim.results; for bits
in result: count=result[bits]`. Native validation must still verify this API.
