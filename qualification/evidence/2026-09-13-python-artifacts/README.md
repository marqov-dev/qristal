# Python artifact acquisition, not installed-runtime qualification

Acquired 12 exact Integrations wheels and 50 Core/tooling wheels for CPython3.10
Linux x86_64. Retained JSON records include file hashes, wheel metadata and base
requirements evaluated for Linux/Python3.10; requirements files bind every acquired
wheel hash. Actual downloads remain in /private/tmp/qb-python-artifacts-20260913.
No package was installed into the product runtime or shared host Python.

The original Core pins are unchanged. setuptools59.6.0 and wheel0.37.1 match the
recorded native Ubuntu toolchain and are explicit additional build inputs.
ANTLR4.9.2 has no matching wheel: its117220-byte PyPI source archive was acquired
and checked against SHA25631f5abdc7faf16a1a6e9bf2eb31565d004359b821b09944436a34361929ae85a.
It has not been built or installed. Therefore the Core wheel set deliberately
reports unmet ANTLR requirements and is not a complete offline install yet.
Integrations base metadata closure passes; native installation/pip-check and
optional-extras closure remain separate gates.

The first download command failed before acquisition because local Homebrew3.14
could not load pyexpat. Bundled Python3.12/pip26.2.1 acquired the artifacts without
changing that interpreter. An initial narrow platform-tag list also missed the
pinned kiwisolver wheel; supplying all manylinux glibc2.5–2.35 x86_64 tags compatible
with Ubuntu22.04 resolved it without changing versions. Downloads used public
PyPI, exact pins, --only-binary=:all: and --no-deps. Metadata inspection uses
packaging26.3 and does not import or execute downloaded code.

Next: build ANTLR from the recorded source with declared tooling on isolated
Linux/Python3.10, hash the resulting wheel, validate complete target installation,
and consume it with configure-time network/pip acquisition disabled. Metadata
checks alone do not prove platform ABI or executable correctness.

Acquisition follows pip's documented cross-platform download procedure:
https://pip.pypa.io/en/stable/cli/pip_download/
