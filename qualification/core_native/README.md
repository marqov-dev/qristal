# Native Core build preparation

Status: frozen materials and unexecuted stage/consumer recipes. This directory
has no AWS runner and is not yet a complete native execution protocol. No Core
configure/build/installation or runtime success is claimed.

`prepare.py CORE DEPENDENCIES XACC PYTHON OUTPUT` accepts the previously verified
Core export, dependency preparation, archive-only XACC transport and acquired
Python artifacts. It requires a new destination, checks locked source and archive
identities, verifies every source tree before/after copying, and copies only named
materials. It also includes the reviewed recipes and consumers. It does not
copy a general checkout, dependency cache or credential directory.

The actual assembled input has fifty acquired Python wheels plus ANTLR source
and its pinned build tools. `material-manifest.json` records the entire inventory,
regular-file/directory modes, relative symlink targets and byte hashes. Symlink
permission bits are excluded because Linux cannot set the host-specific values;
links must resolve within the input root. The manifest is an integrity receipt,
not publisher authentication. A future runner must bind its SHA256 before using
`verify_materials.py`; an attacker-controlled manifest cannot attest itself.

## Work copies and stages

`native/stage_work.py stage` is intended for a Linux container with `/inputs`
read-only and a new bounded `/work`. It verifies the material manifest and makes
fresh derived Core, dependency and installed-XACC copies. It never executes an
installed binary. Core writes a generated header inside its source; after
configure, `stage_work.py audit-core` accepts exactly
`include/qristal/core/cmake_variables.hpp` and rejects every other source change.
The pristine input is never writable. Dependency configure writes and Core's
plugin additions to XACC need their own separately retained mutation inventories.

The shell recipes are documented in [README-stage.md](README-stage.md). Build
only `core pycore xacc-plugins`; the upstream default also includes unrelated
test targets. System Fortran/OpenBLAS and the complete Python environment are
needed even with MPI/TNQVM/TKET disabled. The builder must contain no `nvq++`.

`consumer/` proposes installed-only CMake/C++ and Python tests through Core's
session API: identity and Bell circuits, 256 shots, strict output checks. These
are two distinct fixtures across two API paths. They have not been compiled or
executed. Use explicit installed module/library paths and omit original source
and build mounts. This is a QPP probe, not broader simulator qualification.

## Before execution

Finish a bounded nonroot/networkless container and disposable-host supervisor
that calls input verification and audits, records actual CMake dependency
selection, builds/installs, and runs the installed-only consumers. Retain full
logs on failure as well as success, with exact resource cleanup. No stage shell
alone supplies these controls.

Output retention must handle Core's absolute plugin symlinks into
`/work/install-core/lib` explicitly. Do not relax the existing XACC archive
verifier. A narrowly defined link normalization or a scope-bound verifier for
both installation roots needs review and replay after transformation. Keep the
original retained XACC archive unchanged.

Only after that concrete protocol is reviewed should a new native Core experiment
be launched. The previous approval and successful cleanup describe the completed
XACC run; this source-only preparation created no new AWS resources.
