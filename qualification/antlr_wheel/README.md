# ANTLR Python runtime wheel input recipe

Status: **prepared and statically inspected, not built or runtime-tested**.
This is the Python runtime 4.9.2 required by the pinned Core Python environment,
not ANTLR's Java compiler or its C++ runtime. No Java or C++ compilation is
declared by this distribution's setup script.

The acquired source has a 527-byte `setup.py`, no `pyproject.toml`, six explicitly
named `antlr4` Python packages rooted at `src`, and a `bin/pygrun` script.
Its only declared dependency is `typing; python_version<'3.5'`, which is inactive
on CPython 3.10. Source metadata declares BSD licensing. The description mentions
Python 3.7; that description is not proof of Python 3.10 runtime compatibility.
Source setup was read from tar members without executing it.

`inputs.json` binds the exact acquired source archive plus setuptools 59.6.0 and
wheel 0.37.1. `build.sh` is a future recipe for a disposable Linux CPython 3.10
environment, not an instruction to install tools on the operator host. Stage all
three artifacts plus `recipe.py`, `build.sh` and `inputs.json` read-only under
`/inputs`, and a new empty writable `/output`. Invoke `sh /inputs/build.sh` only
inside a bounded container with **`--network none`**, no credentials, a known
image digest, and a 120-second limit. Retain stdout/stderr and the image digest.

The script creates a dedicated venv using the image's ensurepip, installs only
the two hash-checked local build-tool wheels without indexes/dependencies, and
runs legacy `setup.py bdist_wheel`. It records the bundled pip version; that pip
version is inherited from the eventual pinned builder image, not yet selected
or independently pinned here. No resolver network access or build isolation is
used. `SOURCE_DATE_EPOCH` stabilizes wheel timestamps, but byte reproducibility
across builder images has not been established.

Expected output is `antlr4_python3_runtime-4.9.2-py3-none-any.whl`, pure Python,
with the declared name/version/license/conditional requirement and `pygrun`.
Verification checks bounded ZIP members, the complete RECORD hashes, metadata,
and absence of unexpected payload paths. It never imports or executes wheel
content. `input-identity.json` hashes the recipe/scripts as actually used, and
`wheel-verification.json` binds build logs/tool reports/output wheel. The initial
source receipt remains `built:false`; wheel metadata verification expressly
does not imply native runtime testing.

Next qualification: build this wheel in the pinned native Core environment,
install it offline there, and exercise the parser paths through Core tests.
Do not claim a tested ANTLR runtime from the synthetic offline verifier tests.

Source record:
https://pypi.org/pypi/antlr4-python3-runtime/4.9.2/json
