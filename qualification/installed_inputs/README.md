# Retained installation inputs

`prepare.py` verifies a private snapshot of the retained XACC archive against its
checksummed report and exhaustive receipt. It never runs a binary or CMake.
The native qualification remains the separately retained source-build evidence;
this helper checks transport/materialization integrity, not simulator correctness.

For transport from any host:

```sh
python3 -B qualification/installed_inputs/prepare.py --archive-only ARCHIVE RECOVERED NEW_OUTPUT
```

For a case-sensitive Linux guest, omit `--archive-only`. Materialization creates
regular directories/files first and links last, using only members already
accepted by the bounded archive verifier. It checks the resulting tree's exact
inventory, bytes, modes and link targets before promoting it to a new output.
Existing destinations are rejected. No tar extraction API executes file paths.

The real retained installation contains case-distinct headers including
`JSON.hpp` and `json.hpp`. A case-insensitive Mac filesystem cannot represent
these simultaneously. The first local attempt stopped on that collision and
created no promoted output; the helper now detects this condition explicitly.
The verified archive-only transport succeeded. Linux materialization and a new
installed-consumer replay remain native gates.

The installation must appear at `/work/install-xacc` in the guest. Its generated
header retains the original build paths; it is not claimed relocatable. Core may
write plugin links into the prefix, so use a fresh derived copy and keep the
reusable archive unchanged. Record the post-install derivative separately.

The retained `xacc-config.cmake` reports `1.0.0-` with an empty source suffix.
Core's `dry_run_CMakeLists.txt.in` accepts prefix substrings, so that check alone
cannot prove selection of a particular XACC revision. The archive/source-manifest
binding must remain authoritative, with `XACC_ROOT` explicitly selected and actual
CMake resolution recorded during the native build. Do not invent a version suffix.
