# Core offline source preparation

Scope: Core at `a5c3e5fa544c07d538974d3a289b19652d483848`, the existing CPU
source lock. This commit contains installed-Eigen fix `d393cf0e118ffa631e61f36148a41c028685ddea`.
Inspected newer checkout `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a` has identical
dependency declaration/helper files; preparation consumes the locked export only.
This lane supports CPU packaging and later hosted execution. Decoder is optional
and is not added to this Core build plan.

## Implemented source transformations

`prepare.py` consumes the approved `core-source.json` and `qristal-core/` export,
checks every source byte with the existing export verifier, and creates a new
copy outside the inputs. The first transformation changes exactly one bound line in
`cmake/dependencies.cmake`: temporary Eigen installation moves from
`CMAKE_CURRENT_SOURCE_DIR/deps/eigen3` to `CMAKE_CURRENT_BINARY_DIR/deps/eigen3`.
The later install rule still copies Eigen into the final Core prefix's
`deps/eigen3`, and its exported configuration still names that installed path.
System-found Eigen behavior remains unchanged. CMake/native behavior is untested.

The second transformation replaces the top-level `git describe` version block
with explicit `PROJECT_VERSION "1.8.1"`. In the inspected public-source cache,
`git describe --tags --abbrev=0 a5c3e5fa544c07d538974d3a289b19652d483848`
returns `v1.8.1`; that tag resolves to ancestor
`a0bcfbf4e56adf443e981469e90013e999015183`. The locked commit is **not** the tag
commit. This preserves the original configure-time version choice for the locked
revision; it does not claim an unmodified upstream release or authenticate a
publisher. Git discovery remains available to other dependency helpers.

The Eigen zero-context patch and version unified diff are review artifacts. The helper applies the equivalent
exact byte replacement only after checking the complete original file SHA256;
it checks the patch bytes too. Manual `git apply` would require `--unidiff-zero`.
Both copies are verified before editing, then the derived copy is verified against
its effective byte manifest. Its changed files do not retain pristine Git blob
identities; the effective manifest does not claim to be the original Git tree.

```sh
python3 -B qualification/core_build/prepare.py /path/to/pristine-core-inputs /new/outside/path
python3 -B -m unittest discover -s qualification/core_build -p 'test_*.py'
```

No CMake, compiler, dependency acquisition, Docker, cloud or publication runs here.
The preparation receipt explicitly says unconfigured and unqualified. It is not
an install receipt or a reason to relabel the existing private CPU image.

## Remaining configure blockers

1. **CPM:** `cmake/add_dependency.cmake:4–14` downloads CPM0.36.0 when absent.
   Capture its existing hash-bound script and provide its expected cache location.
   Provide explicit source overrides for all eleven locked dependencies; do not
   assume the old CPM cache directory keys are Git commits. CPM package selection,
   patches and configure writes need a controlled fresh working area. Keep the
   pristine dependency exports immutable; derive any patched source copies first.
2. **Python:** preinstall the complete hash-locked Linux amd64/Python3.10 wheelhouse
   into a fresh interpreter environment before offline configure. Set
   `INSTALL_MISSING=CXX` so Core cannot invoke pip; this permits C++ dependency
   setup while disabling automatic Python installation. Core0.46 and Integrations1.2
   refer to their Qiskit environments, not Core product versions. Integrations
   remains a separate installation/qualification, not part of this first build.
3. **Fresh XACC:** supply its retained installed artifact and manifest, set
   `XACC_ROOT`, `XACC_TAG`, and `XACC_REPOSITORY` explicitly. The latter must use
   public XACC; otherwise Core's default still names the old QB GitLab repository.
   Confirm `add_poorly_behaved_dependency` accepts the installed version/tag rather
   than entering its clone/build fallback. A disconnected configure must fail if
   it cannot select these declared inputs; no network retry.

## Explicit build directory map

Use a fresh isolated build root and install prefix. Source exports mount read-only.
Build output, CPM working/staging area, Eigen temporary install, Python package-info
output and final installs are the only writable paths, plus bounded scratch.

| Input/output | Intended location and control |
| --- | --- |
| Patched Core source | `/inputs/qristal-core`, read-only, effective manifest |
| Pristine dependency exports | `/inputs/deps/<name>`, read-only, source receipts |
| CPM working area | `/work/deps`, fresh; preload captured CPM script; explicit source overrides |
| Core build / temporary Eigen | `/work/build-core`, fresh, writable |
| Final Core | `/work/install-core`, fresh, writable |
| Python package-info file | `PYTHON_PACKAGES_PATH=/work/install-core/python-site` |
| Fresh XACC prefix | `/work/install-xacc`, declared installed artifact |

`cmake/py_packages_path.cmake:81` writes a `.pth` during configure, so its explicit
path must be writable and bounded. `cpp_lib.cmake:274,286` already generates package
configuration files in the current binary directory. Core's dependency installer
can write plugin symlinks into `XACC_ROOT/plugins`; do not silently mutate a reused
XACC artifact. Audit whether selected targets need those writes, then use a fresh
manifest-bound derivative prefix or install-layout transformation before install.

Predeclare `WITH_MPI=OFF`, `WITH_TNQVM=OFF`, `WITH_TKET=OFF`, no profiling additions,
the chosen optimization flags and named CPU targets. Inventory actual resolved
system Boost/OpenSSL/OpenBLAS/Python development components from the builder.
System package discovery can bypass a source override; retain the actual selection.

## Next evidence gate

After the blockers are resolved, run one bounded native offline configure/build,
install into fresh prefixes, and use installed-only Core QPP fixtures and a CMake
consumer. Retain complete source/dependency/patch/toolchain receipts and installed
file/mode/link hashes before cleanup. Then build and qualify a new distributable
runtime identity. Do not expand this into full Decoder or require changes to the
main agent's hosted execution contract.
