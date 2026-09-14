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

The Eigen and dependency-path zero-context patches and version unified diff are review artifacts. The helper applies the equivalent
exact byte replacement only after checking the complete original file SHA256;
it checks the patch bytes too. Manual `git apply` would require `--unidiff-zero`.
Both copies are verified before editing, then the derived copy is verified against
its effective byte manifest. Its changed files do not retain pristine Git blob
identities; the effective manifest does not claim to be the original Git tree.

The third transformation addresses the first native configure failure in
`cmake/add_dependency.cmake`: a missing package path expanded to no macro argument
at line 81. Both existing `is_in_install_path` calls now quote their path arguments;
both already had a result argument, and those result arguments are preserved.
The helper initializes the result OFF and skips `REAL_PATH` for empty/unset paths,
`NOTFOUND`, and names ending in `-NOTFOUND`. Valid paths and the installation
prefix are quoted when canonicalized. `cmake_path(IS_PREFIX ... NORMALIZE)` checks
path-component boundaries, avoiding the former string-prefix false positive for
`/install-sibling` versus `/install`. Its syntax is supported since CMake3.20 and
by the builder's CMake3.22.1; see the
[CMake3.22 command reference](https://cmake.org/cmake/help/v3.22/command/cmake_path.html).

This transform accepts only original file SHA256
`a1f682dcd200418ed36c584a86ed7b4733870b2c525d734f6673ba0440bfa76c`.
The resulting file SHA256 is
`37480e0849a7cb4865ae3189213c67e979696853f98b723e8e1db46d29530502`.
`dependency-path-guard.patch` is checked against the exact generated diff before
preparation writes any output. The receipt separately binds original/derived file
hashes and patch hash, and the effective manifest records the third changed file.
The path-guard transformation itself changes no find-package selection or CPM
audit behavior. The scoped override transformation below replaces the need for
global package-disabling flags, which otherwise also suppress required nested
lookups in dependencies.

The regression extracts only this macro and its two call sites into a minimal
`cmake -P` script; it never includes CPM, configures Core or builds a library.
Cases cover empty, unset, NOTFOUND, identical, child, outside, prefix-sibling and
space-containing paths. Locally the CMake test skips if no existing executable
is available. CI must set `QB_REQUIRE_CMAKE_TESTS=1` to make missing CMake fatal;
`QB_CMAKE` may identify an existing executable. Native configure success remains
unverified until the separately frozen experiment is rerun.

## Scoped source selection and nested Eigen configuration

The next native configure passed the original macro-argument failure and exposed
two further integration problems: global find-package disabling also blocked
dependencies' own required lookups, and Eigen's nested configure/install commands
did not propagate failure before their build directory was deleted.

`dependency_selection.py` accepts only the exact path-guard output SHA
`37480e0849a7cb4865ae3189213c67e979696853f98b723e8e1db46d29530502`.
When `CPM_${NAME}_SOURCE` is explicitly defined and nonempty, it skips only Core's
initial optional `find_package` and clears the corresponding `_FOUND` variable,
so a stale ambient package cannot win over the declared source. Otherwise the
original lookup, including its versions/options, is preserved. No global
`CMAKE_DISABLE_FIND_PACKAGE_*` variable is written, so a dependency's later
`find_package(... REQUIRED)` still operates normally. Native stage flags must
remove those global disables separately, and actual CPM selections must still
pass the existing independent audit.

`eigen_configure.py` accepts only the exact staged-Eigen dependency file SHA
`342cc2bcf56d5c90944cc4e332d20e70f258e72e6f27a258778f7080408d93b1`.
It replaces Eigen's three unchecked child commands with explicit quoted `-S`
and `-B` arguments, disables `BUILD_TESTING`, `EIGEN_BUILD_TESTING` and
`EIGEN_BUILD_DOC` (all declared by the locked Eigen source), and checks configure
and installation status separately. A failed configure stops before installation;
a failed installation is fatal. The temporary build directory is retained for
CPM and diagnostic evidence. The intended install prefix and final exported
Eigen layout remain unchanged.

Both changes have separately checked zero-context patches, intermediate/final
file hashes and receipt fields. Final `add_dependency.cmake` SHA is
`9c0d7edab059e541709ce04d3e985a58dfa5247300089bc0a36fd59b0d7bb18a`;
final `dependencies.cmake` SHA is
`9598f7727fb593e95db8d4d2a62792a4c59cfae6ae1b3f91caa355be14a1117a`.
The resulting effective source manifest SHA is
`6ab2ab67c277275b21878742d0088cb4337626336cbb088b310ab92b2e4c75bf`.

Additional script-only regressions inject mock find-package/CPM behavior to
check explicit override precedence, stale `_FOUND` clearing, preserved nested
required lookup and unchanged absent/empty-override behavior. Eigen tests use a
small fake child executable, not a compiler or project configure, to check
quoted space-containing paths, disabled tests/docs, failure propagation, ordering
and retained build directory. They follow the same strict-CI CMake requirement
as the path-guard regression. No full Core build success follows from these tests.

```sh
python3 -B qualification/core_build/prepare.py /path/to/pristine-core-inputs /new/outside/path
python3 -B -m unittest discover -s qualification/core_build -p 'test_*.py'
```

No CMake, compiler, dependency acquisition, Docker, cloud or publication runs here.
The preparation receipt explicitly says unconfigured and unqualified. It is not
an install receipt or a reason to relabel the existing private CPU image.

## Remaining configure blockers

1. **Actual C++ dependency selection:** [Core dependency preparation](../core_dependencies/README.md)
   provides all eleven explicit source overrides, the pinned CPM0.36.0 script and
   a verified Eigen copy with the required patch already applied. CPM's source
   override omits patch commands. Native configure must still prove its actual
   selections: Core's earlier system-package discovery can bypass the overrides.
2. **Python:** the acquired Linux amd64/Python3.10 wheelhouse needs the remaining
   ANTLR4.9.2 source built as a wheel; see [its offline recipe](../antlr_wheel/README.md).
   A fresh native environment must pass installation and dependency checks before
   offline Core configure. Set `INSTALL_MISSING=CXX` so Core cannot invoke pip.
   Core Qiskit0.46 and Integrations Qiskit1.2 remain separate environments.
3. **Fresh XACC consumption:** the complete freshly built installation is retained
   and verified. [Installed-input preparation](../installed_inputs/README.md)
   preserves it as a transport archive; extraction needs a case-sensitive Linux
   filesystem. Use `/work/install-xacc` explicitly with `XACC_ROOT`, `XACC_TAG` and
   public `XACC_REPOSITORY`; record actual CMake selection. Its installed version
   suffix is empty and Core accepts version substrings, so only the bound source/
   artifact manifest proves revision identity. Installed-only replay after
   extraction and final Core install remain required.

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

[Native materials and stage preparation](../core_native/README.md) now assembles
the verified inputs and proposes installed-only fixtures. It is not yet the
bounded native supervisor or a successful Core build.

After the blockers are resolved, run one bounded native offline configure/build,
install into fresh prefixes, and use installed-only Core QPP fixtures and a CMake
consumer. Retain complete source/dependency/patch/toolchain receipts and installed
file/mode/link hashes before cleanup. Then build and qualify a new distributable
runtime identity. Do not expand this into full Decoder or require changes to the
main agent's hosted execution contract.
