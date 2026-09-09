# Public CPU image — local qualification

A self-contained Linux amd64 image now runs the previously qualified CPU workload without host mounts, source/build trees, private QB libraries or a compiler. It is a local experimental runtime, not a deployed Marqov executor. The [adapter proposal](ADAPTER-PROPOSAL.md) awaits the release owner's boundary review.

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
