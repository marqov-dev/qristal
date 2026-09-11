# Offline GPU candidate mapping experiment

This implements the next offline review step from the hosted-profile proposal.
It consumes saved CUDA-Q candidate observations and local expectations to produce
an **unaccepted display preview**. It defines no platform wire schema, admission
record, provider identity, result receipt, resource-release action or engine hook.

## Independence of expectations

`replay.py` constructs input artifacts from the six pre-existing analytic circuit
fixtures, target choices, 16,384 shots and seed 42. Runtime image, adapter SHA-256,
CUDA-Q version and library paths are separately fixed to the reviewed native
qualification. None of these expectations is populated from a candidate being
validated. The old evidence's `artifact` object is not used to construct context.

`mapping.py` checks exact input bytes against the independently supplied input
hash, verifies input target/qubits/shots/seed against expectations, and checks the
closed gate vocabulary. It then checks a bounded candidate JSON with duplicate
key rejection, exact fields/types, runtime/adapter/input binding, target, explicit
GPU profile, bit order, library list and shot/count constraints. Unknown operations,
missing output and CPU substitution fail closed. Runtime library strings remain
claims, checked against expected fixture values; they are not authentication.

The preview preserves counts, adds an explicit ordered `q[0]`…`q[n-1]` map and
complete-sampling accounting. It does not manufacture a physical device map,
Braket ARN, accepted-state flag or authority identifier. The same mapper runs for
synthetic `direct_v1`/`temporal_v1` labels; equality is **mapping parity only**, not
execution by either real engine or qualification of either orchestration path.

## Evidence and checks

Twelve saved native candidates replay successfully: six cases per GPU target.
The analytic expectations also check the retained counts independently. Twelve
regression tests cover the matrix and rejection of changed placement, runtime and
input hashes; matching malicious candidate/input target claims against a different
expected target; missing/extra output; wrong bit maps; boolean/floating counts;
duplicate JSON keys; invalid encodings; unsupported gates and size limits.

One explicit limitation test preserves plausible but wrong counts: a structurally
valid, correctly bound distribution is not proof that its quantum circuit executed.
Analytic circuit checks belong to qualification; authenticated runtime provenance
and platform acceptance remain separate requirements. Caller-created expectations
are not granted authority merely by constructing this Python dataclass.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=qualification/gpu_mapping \
  python3 -m unittest test_mapping
PYTHONDONTWRITEBYTECODE=1 python3 qualification/gpu_mapping/replay.py
```

No AWS, Docker, CUDA-Q install, database, service or network is required. See
[retained replay evidence](../evidence/2026-09-11-gpu-mapping/README.md).

## Remaining work

The reviewed platform must independently resolve authenticated expected context,
select/accept a provider-neutral output schema, and bind the exact task/request,
runtime and acquisition through existing authorities. This local display shape
is not that schema. Immutable derivative packaging and hosted identity/transport,
provider reconciliation and isolation qualification remain open as described in
[the profile review](../gpu_adapter/HOSTED-PROFILE-REVIEW.md). There is no admission,
new hosted result or release-critical dependency introduced here.
