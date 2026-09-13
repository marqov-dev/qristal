# Source-built Core packaging input gate

This read-only gate produces an inventory and next-step plan, **not a runtime**.
It does not extract files, install dependencies, build containers, publish or
contact a cloud service. Its inputs are the retained Core output archive,
executed protocol, executed `material-manifest.json`, and recovered native receipt (either the raw report or the
existing `{"result": ...}` envelope).

```
python3 -B qualification/core_package/audit.py OUTPUT.tar.gz protocol.json recovered.json material-manifest.json --output NEW-packaging-inputs.json
```

Both existing validators must accept the evidence: `core_output/output.py`
checks the archive/receipt/report and `core_native/check_result.py` checks the
native stage contract and full logs. Their current file hashes must match the
executed protocol; mismatched validator versions require a separately reviewed
compatibility decision. No duplicate archive extraction or link-validation rules
are introduced here. Missing, failed, conflicting or altered receipts fail
closed; the CLI writes no plan until validation succeeds and never overwrites an
existing plan.

The supplied material manifest is bounded to 32 MiB and its raw SHA256 must
match `protocol.materials_sha256`. Its `python/core.json` entry must bind the
checked-in wheel manifest's exact bytes/hash, and all 50 wheel entries must
match that manifest's regular-file type, size and SHA256. Missing entries,
duplicate JSON keys or wheel names, and extra wheel entries are rejected.
This connects the packaging wheel requirements to the inputs the native
execution actually verified, rather than only to the current repository state.

The resulting plan binds archive, protocol, native receipt, checker and audit
hashes; copies the already-verified retained file/mode/link inventory; lists the
50 required locked Python wheels plus retained ANTLR wheel; and records the
runtime/system ABI and notice work still needed. The wheel list is a requirement
from the checked-in acquisition manifest, not a claim that those wheel bytes
were supplied or installed by this gate. Native observations remain QPP-only.

Next work requires a new staged context that preserves the validated sibling
`install-core`/`install-xacc` layout, reconstructs the Python environment offline,
binds adapter and capability files, selects final OS dependencies, and tests the
assembled image without source/build mounts. Historical apt pins are references,
not proof of ABI compatibility with the final image. Aer, Integrations, Decoder,
public distribution, bit reproducibility and hosted admission are separate gates.

Tests use synthetic receipts and the existing native-checker fixture. They test
the preparation boundary and rejection behavior; they do not run a simulator.
