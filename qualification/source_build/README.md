# Fresh source-build experiment

This is the next step after clean Git-object reconstruction. Read [PLAN.md](PLAN.md)
for the fixed hardware, deadlines, scope and evidence limits before execution.
It reuses the independent CPU VM supervisor and does not touch shared Docker,
platform code, SDK code, existing source checkouts or installed prefixes.

```sh
python3 -B qualification/source_build/prepare.py /path/to/pristine-inputs /tmp/new-source-artifact
python3 -B qualification/source_build/run.py /tmp/new-source-artifact /tmp/new-source-run
```

Preparation verifies the retained clean manifests, copies the two source trees
into a new directory, applies the two compatibility patches and the recorded build-output patch and copies only the
named Boost archive. It verifies the copied source bytes before patching and
records the effective input file/link/directory identities afterward. Non-root
readability and traversal are checked before packing. Patches do not alter the
pristine input directories. The archive receipt binds all transferred inputs.

Running creates one temporary AWS CPU instance, private transfer bucket and
security group in the existing fixed qualification account. This is an explicit
native execution command, never an offline CI test. The toolchain is constructed
from the pinned public Ubuntu base and captured recipe. Source configuration,
compilation and tests then run without network access, with bounded resources and
fresh build/install directories. A separately compiled consumer reads only the
installed headers/libraries and runs without source/build mounts.

The local `transfer.json` and `vm/` directory retain exact recovery/cleanup state.
Do not publish raw operator records without reviewing infrastructure identifiers.
Only checksummed result chunks are recovered; full guest logs/installations are
not exported. Recovery and cleanup success do not imply native tests passed.
The report must identify which stage failed or confirm all required stages before
making a narrower qualification claim. This does not publish a new runtime.

The [first native result](../evidence/2026-09-13-xacc-source-build/README.md)
reached offline compilation but failed on ANTLR source-tree output. It did not
reach installed tests. Current preparation includes a separate output-directory
correction for the next run; read its recorded outcome before claiming success.
