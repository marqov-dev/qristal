# Public CPU image — local qualification

A self-contained Linux amd64 image now runs the previously qualified CPU workload without host mounts, source/build trees, private QB libraries or a compiler. It is a local experimental runtime, not a deployed Marqov executor. The release owner reviewed the [adapter proposal](ADAPTER-PROPOSAL.md) and approved the workload-local adapter and conformance slice only. Hosted QB artifact/profile admission is not yet defined.

The qualified local image ID is recorded in `../evidence/2026-09-09-runtime-image/runtime-image.json`. No image was pushed to a registry. Do not confuse this local image/config ID with a registry manifest digest required by hosted admission.

## Build and test

Start from the installed-runtime workspace in `../installed/README.md`, using merged Core `a5c3e5fa544c07d538974d3a289b19652d483848`, Decoder `13bb8f80f98bd259196834a13817c23ec02480e6`, Integrations `16e4941ef5ad8476ad971a366ecce91e5ea5bd45` and the public XACC/profile pins. Prepare the installed fixtures and build the small decoder test consumer before image assembly.

```sh
python3 qristal/qualification/runtime/build_image.py
python3 qristal/qualification/runtime/test_image.py
```

The builder uses the digest-selected public Ubuntu 22.04 base and version-selected runtime packages, copies qualified native libraries/plugins and the two separate Python dependency installations, includes public-source license/notice texts (including Boost) and preserves Python package license metadata and Debian copyright files. It does not copy a host home, backend database, source checkout or credentials. The final process user is 65532. Public apt acquisition is networked; tests are offline. Build containers are limited to 2 CPUs, 4 GiB including swap and 256 PIDs. No registry push or deployment is performed by these scripts.

The two Python environments are intentional: Core's earlier build uses Qiskit 0.46; the V1 Integrations adapter is tested with Qiskit 1.2. The adapter environment is selected only for its qualification checks. The normal circuit CLI uses the Core environment.

Apt's selected top-level versions are pinned and the full resolved package inventory is recorded. Rebuilding still depends on public repositories retaining those versions; apt repositories are not snapshot-pinned and byte-identical rebuilds are not claimed. The final immutable image ID pins the tested local artifact. Native file hashes, source commits and Python locks accompany the evidence.

## Result

Ten image test groups pass, including all 43 prior CPU functional fixtures (ideal Core, Aer noise, Qiskit primitives and simplified Decoder), capability reporting, ideal/noisy Bell CLI runs, rejection of out-of-bounds shots and unsupported GPU selection, and non-root/no-source/no-compiler checks. All run with **no host mounts**, no network, a read-only root, bounded scratch space and dropped capabilities. Tests have an outer 180-second process limit; a hosted controller must supply its own admitted deadline and termination/recovery behavior.

At 4096 shots the local CLI demo returned:

| Model | 00 | 01 | 10 | 11 |
|---|---:|---:|---:|---:|
| Ideal qpp | 2022 | 0 | 0 | 2074 |
| Aer readout error on qubit 0 (p10=.2, p01=.1) | 1639 | 224 | 383 | 1850 |

Counts use qubit 0 first. The noisy expectation is .4/.05/.1/.45 respectively. This is a public analytical readout model, not a QB hardware calibration or commercial Emulator model.

The initial assembly copied two directories one level too deep. A local assembly correction copied their contents to the intended paths; both image IDs and that lineage are retained. The source recipe now uses explicit directory-content copies. Final validation ran against the corrected immutable image, not the intermediate one.

## Interface and limits

The default command reports capabilities. The local workload CLI accepts an OpenQASM file, qpp/Aer selection, bounded qubit/shot counts and optional Aer readout probabilities. It emits a local experimental counts record. It does not consume `marqov.execution-request/v1`, authenticate a job, submit provider work, promote artifacts or update customer state. Only the trusted platform boundary can do those things.

The image contains additional installed libraries and qualification fixtures. They are not automatically advertised as hosted capabilities. The image is compiler-free. Minimizing it, publishing a registry artifact and registering the hosted runtime profile are separate steps. GPU/tensor backends, commercial Emulator/vQPU, full quantum Decoder, Qiskit V2, hosted cancellation and end-to-end platform execution remain outside this result.

## Workload-local adapter qualification

`adapter.py` separates bounded input/result validation from the CLI. It preserves
`local-qristal-sample/experimental`, hashes the original input bytes, checks exact
shot totals and emits qubit-0-first counts. Inputs are UTF-8 OpenQASM 2, at most
64 KiB, with one qelib1.inc include and one matching qreg; qubits are 1–12,
shots 1–16384 and seeds 0–2147483647. Nonzero readout probabilities require Aer.
File reads reject symlinks and non-regular files. The precheck is not a complete
QASM parser: circuit parsing remains inside the isolated native engine.

The CLI suppresses native diagnostics and emits bounded static errors. It is
intended for a fresh single-process workload, not concurrent calls inside a
trusted web service. Native aborts or exits still require an external controller
to enforce a deadline and require a valid result; exit status alone is never
proof of success. The counts describe qubits in order, not a general classical
register mapping. Only the tested full-register measurement cases are qualified.

Run pure tests without native dependencies:

```sh
python3 -B -m unittest discover -s qualification/runtime -p test_adapter.py
```

To reproduce the local derivative and native conformance tests from an already
qualified local CPU image, use its immutable image ID:

```sh
python3 qualification/runtime/qualify_adapter_image.py --parent IMAGE_ID --output /tmp/qristal-adapter-evidence
python3 qualification/runtime/test_image.py --image DERIVED_IMAGE_ID
```

The overlay script copies only the adapter, CLI and tests, then runs both test
modules with no network, no host mounts, read-only root, 128 MiB scratch, 2 CPUs,
4 GiB including swap, 256 PIDs and a 240-second outer deadline per command.
The clean image assembly recipe also includes adapter.py.

See [adapter evidence](../evidence/2026-09-09-adapter/README.md). No platform gate,
SDK/compiler interface, provider identity, artifact schema, cancellation path or
hosted status is changed. Platform admission currently supports Python task
materials; a future QB profile must explicitly specify its program/result schemas
and trusted lifecycle before this workload can be connected.

## Independent local candidate validation

`candidate.py` independently checks the local CLI record against caller-supplied
program bytes, backend, qubit count and shots. It rejects duplicate JSON keys,
unknown/missing fields, trailing data, invalid counts, inconsistent totals and
nonzero process exits. The result is an immutable `LocalCounts` value with explicit
positional qubit labels. This does not authenticate execution, prove that a circuit
was run, certify its measurement semantics or produce a hosted result artifact.
Expected facts must eventually come from the platform's admitted request; the local
harness supplies fixed fixtures. The CLI format does not bind seed/options/runtime
identity, so those facts need separate trusted provenance before hosted promotion.

`bounded_process.py` is a POSIX qualification helper for fixed commands. It bounds
both output streams while reading, enforces a deadline even when pipes close early,
and kills the process group on exit. It is not a container scheduler or a hosted
cancellation implementation. Its caller owns container cleanup; container/provider
termination must be independently observed in a hosted implementation.

```sh
python3 -B -m unittest discover -s qualification/runtime -p test_candidate.py
python3 -B -m unittest discover -s qualification/runtime -p test_bounded_process.py
python3 qualification/runtime/qualify_candidate_image.py --parent IMAGE_ID --output /tmp/qristal-candidate-evidence
```

The last command adds only candidate-validation and qualification files to an
existing local CPU image and runs fixed fixtures offline without host mounts. It
neither changes the native runtime nor rebuilds it. See the
[candidate evidence](../evidence/2026-09-09-candidate/README.md): nine unit test
methods and 29 image-harness checks passed, including six real simulator runs.
Parser-based hosted circuit restrictions, material staging, attestation, registry
publication and hosted result/lifecycle wiring remain separate work.

## Restricted parser qualification

`program_guard.py` is an additional experimental profile, not a change to the
existing CLI. Run it only in the bounded, credential-free CPU container. It uses
the installed Qiskit 0.46 OpenQASM 2 parser in strict mode with an empty include
search path; the existing byte/include precheck runs first. No dependencies are
installed. The parser's built-in qelib1 support remains available.

The profile accepts only X, H and CX operations, one quantum and one classical
register of matching size, and complete final measurements in positional order.
Expanded individual measurements equivalent to that final block are accepted.
Other executed gates, barriers, reset, classical conditions, partial/reordered or
mid-circuit measurements are rejected. Total parsed operations, including final
measurements, are capped at 4096; input and canonical output are capped at 64 KiB.
Unused declarations are not an advertised capability; executable instructions
must all belong to the closed profile. Limits apply after parsing, so the parser
itself still requires the outer CPU/memory/deadline boundary.

The guard emits fresh OpenQASM with fixed q/c registers and only validated
instructions. This avoids forwarding arbitrary source to a second native parser.
It returns the original source hash separately. The native result hash refers to
these canonical bytes: a future trusted integration must bind original and canonical
artifacts rather than mislabel one hash as the other. The guard's returned hash is
not an attestation or independent proof that normalization happened correctly.

```sh
python3 qualification/runtime/qualify_program_image.py --parent CANDIDATE_IMAGE_ID --output /tmp/qristal-program-evidence
```

Use the qualified candidate image from the preceding section; the harness depends
on its bounded process helper and candidate validator. The command adds only the
guard and tests. See [parser evidence](../evidence/2026-09-09-program/README.md).
Supporting arbitrary QASM, parameterized rotations, noise, or compiling customer
Python requires separate qualification. Hosted material staging, provenance and
lifecycle integration remain unimplemented.

### Joined local experiment

`local_pipeline.run_local(program_bytes, options_bytes, backend='qpp')` joins the
restricted parser, fixed simulator CLI and independent result validator. Options
are at most 1024 UTF-8 JSON bytes, with exactly integer `qubits`, `shots`, `seed`;
backend is qpp or Aer and this path is ideal-only. Unknown/duplicate keys, invalid
types and bounds fail before parsing. Rejected circuits never start the simulator.
Temporary canonical files are removed after success or failure. The whole call,
including the parser, must remain inside the qualified isolation and outer deadline.

The returned immutable `LocalObservation` separates the original source hash,
canonical source hash and exact options-byte hash. Its nested local result refers
to the canonical circuit actually sent to the CLI. These are local bookkeeping
facts, not authenticated provenance or a hosted receipt. Options and source bytes
come from the experiment's caller; no material gateway or admission is simulated.
The pipeline does not select a provider resource, grant retries or release capacity.

The existing `qualify_program_image.py` command now also runs this pipeline's tests.
The latest [joined evidence](../evidence/2026-09-09-program-pipeline/README.md)
records the derived image and logs. The existing image entrypoint and CLI remain
unchanged; this helper is an additional local experiment, not the hosted adapter.

### Local preparation binding and file-staging fixtures

`preparation_binding.py` tests a local four-file preparation bundle: original QASM,
canonical QASM, exact closed options JSON and dependency-lock bytes. A separately
retained local manifest records their hashes, backend/settings, logical measurement
map, parser package version/guard hash and supplied image/lock policy. Verification
rehashes files and recomputes canonical preparation inside isolation before result
validation. It rejects unknown/symlink files, duplicate JSON and changed facts.
Verified byte snapshots must be used for execution rather than rereading mutable
paths. The fixture directory is caller-owned; this is not a race-proof shared-filesystem
or cross-tenant delivery protocol.

Image and dependency-lock policy in these fixtures are deliberately synthetic,
not an actual registered runtime profile or attestation. The lock hash check proves
byte binding only; it does not prove the running dependencies match that lock.
Parser package version and guard hash do not pin all parser/native dependencies.
A hosted implementation must independently authorize the retained facts, validate
image/lock identity and protect original-to-canonical preparation evidence. A
workload that supplies its own replacement manifest can fabricate consistent facts.

```sh
python3 qualification/runtime/qualify_binding_image.py --parent PIPELINE_IMAGE_ID --output /tmp/qristal-binding-evidence
```

The parent must be the qualified joined-pipeline image. The command adds only local
binding code/tests and runs offline, with no host mounts or credentials. See
[binding evidence](../evidence/2026-09-09-binding/README.md). No material gateway,
hosted schema, credential-bearing stager or deployment topology is implemented.

### Disposable-host microVM proof

The joined CPU image also passed a bounded qpp experiment inside Firecracker/KVM,
including fresh preparation/validation guests and kill/output-limit cases. See
[reproduction and offline evidence checks](../microvm/README.md). This is separate
from the earlier container matrix and does not enable a hosted executor.

### Restricted readout-noise demo

`local_pipeline.run_readout(program_bytes, options_bytes)` now joins restricted
X/H/CX preparation, **Aer** execution and candidate validation with readout error
on logical qubit zero. The exact closed options are:

```json
{"qubits":2,"shots":16384,"seed":42,"readout":{"p10":0.2,"p01":0.1}}
```

`p10` means P(report 1 | prepared 0); `p01` means P(report 0 | prepared 1).
The other measured qubits have no readout error in this profile. Probabilities
must be finite numbers in [0,1]; booleans, missing/extra/duplicate fields and
invalid resource options are rejected before circuit parsing. The existing
`run_local` API remains ideal-only and rejects the new noise options. The new
entrypoint fixes Aer explicitly; failure never retries through QPP.

Use the same restricted QASM described above. For example, prepare zero and then
compare with X on q[0]: with p10=.2/p01=.1 the expected reported-one probabilities
are .2 and .9. A Bell circuit illustrates how asymmetric readout error turns the
ideal `00`/`11` distribution into four outcomes. These are analytic toy examples,
not a calibration model for a QB device or a substitute for its commercial emulator.

One command runs the boundary/regression tests and all eleven fixed analytic cases:

```sh
python3 qualification/runtime/qualify_readout_image.py --output /tmp/qristal-readout-new-run
```

It requires the already-qualified local linux/amd64 image
`sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44`.
It refuses an existing output directory and does not pull, rebuild or publish
images. Two fresh containers receive exact source overlays in bounded `/tmp`;
the native CLI source is checked against the overlay before execution. No host
filesystem is mounted. The native binary image stays unchanged. This is a **source
overlay qualification**, not a claim that the older image already contains the new
helper. A machine without that image must first follow the earlier runtime build
and qualification steps; those steps do not guarantee a byte-identical image.

The harness uses non-root UID/GID 65532, network none, read-only root, 128 MiB tmpfs,
two CPUs, 4 GiB memory, 256 PIDs, no capabilities and no-new-privileges. Each stage
has a 240-second outer deadline, 128 KiB stdout and 16 KiB stderr limits. Inner
simulations retain their 60-second bound. Output-limit/deadline errors trigger
owned-container removal; Docker cleanup failures are errors. Recorded names and
labels identify only this run. Abrupt host failure can leave a container: inspect
and remove the exact recorded name only after verifying its `qristal.readout`
label matches; a missing final manifest is incomplete evidence, not a retry grant.

The evidence can be checked **without Docker or Qristal installed**:

```sh
python3 qualification/runtime/check_readout_evidence.py
PYTHONPATH=qualification/runtime python3 -m unittest test_readout_evidence
```

See [retained observations and limitations](../evidence/2026-09-11-readout-pipeline/README.md).
This does not widen any Marqov hosted schema or enable a backend selector. The
previous four-artifact preparation-binding helper is still ideal-only; a hosted
noise material/acceptance binding requires a separate agreed contract. Noisy options
are bound to exact bytes in `LocalObservation`, not attested by the native result.
