# Core native selection gate (not executed natively)

The first experiment requires all eleven captured C++ dependencies through CPM,
with exact case-sensitive source paths. `check.py` reads **actual**
`CPM_PACKAGE_<name>_SOURCE_DIR:INTERNAL` and corresponding binary-directory
entries written by captured CPM0.36.0 `cpm_store_fetch_properties`, rather than
trusting requested `CPM_<name>_SOURCE` overrides. It rejects omitted/replaced
sources, noncanonical/outside build paths, duplicate cache keys and wrong
Core/XACC prefixes. It is a check of CMake's recorded selection, not proof of
compiled target linkage or a signature over untrusted cache bytes.

The source-preparation helper bypasses Core's optional ambient lookup only when
that dependency has an explicit nonempty `CPM_<name>_SOURCE` override. Configure
must not globally disable package discovery: dependencies such as autodiff need
`find_package(Eigen3 REQUIRED)` against the Eigen installation just created by
Core. `check.py` rejects enabled global disable flags while still requiring all
eleven actual CPM selections. An override alone never satisfies the gate.

System Python, Boost, OpenSSL, OpenMP, BLAS and CURL remain explicit builder
dependencies. Record their versions and actual paths in native inventory and
configure logs; this checker does not qualify those versions.

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

The [retained repeat failure](../evidence/2026-09-13-core-eigen-configure/README.md)
establishes that the previous global flags blocked a nested required Eigen
lookup. The revised scoped lookup and checked Eigen setup require another native
run; neither has passed this selection gate yet. Unexpected source writes still
require a narrow documented correction, never silent acceptance.

Python fixture review: locked Core's `MapVectorBoolInt` manually exposes key
iteration and `__getitem__`, but no `.items()` method
(`src/python/py_stl_containers.cpp:131–187`). Use `result=sim.results; for bits
in result: count=result[bits]`. Native validation must still verify this API.
