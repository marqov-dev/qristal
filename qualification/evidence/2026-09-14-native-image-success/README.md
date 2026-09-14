# Source-built QPP image: native AMD64 success

The one authorized m7i.large experiment passed all nine checks. The exact PR49
image was loaded on an observed empty Linux x86_64 Docker daemon, after its saved
archive, OCI descriptors and layer hashes were verified. The loaded complete
runtime configuration and diff-ID chain matched the archived image. No source
compilation or simulator image rebuild occurred on this VM.

Executed source: `af34b9d59be0ad337427046b28a14e7cbb8e9896` (PR50), merged as
`ef954daf725168b58608e39e600d79327d1906a6`. Image index:
`sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f`.
Config: `sha256:0127d58acfa19aae8fe4ab911b1acbb9993d8ab16ebd40ad55421480457907f0`.
The native engine resolved the index directly; the config-ID fallback was not
needed in this run. Other engine-version behavior remains unqualified.

| Native check | Observed result |
|---|---|
| Capabilities | QPP-only surface accepted |
| Identity circuit | `00: 256` |
| Bell circuit | `00: 141`, `11: 115`; 256 total |
| Asymmetric q0 circuit | `10: 256`, confirming qubit-0-first convention |
| Aer request | Rejected with the expected diagnostic |
| Nonzero noise request | Rejected with the expected diagnostic |
| Imports | Core, NumPy, SciPy, SymEngine and Qiskit imported |
| NumPy operations | Matrix product, solve and SVD reconstruction passed; mapped libraries recorded |
| SciPy operations | Matrix product, solve and SVD reconstruction passed; mapped libraries recorded |

These are nine checks and three distinct QPP circuits, not nine simulators.
Imports alone do not qualify Qiskit integration or the broader Core API.
The unsupported Aer/noise checks prove rejection, not those capabilities.

The raw result envelope is 82,822 bytes, SHA256
`c4f9eddd336b8cc74663b93b31472019b9f27ce053e0b1d49f771b51f8e5a705`.
It preserves exact execution/probe JSON text and the frozen native protocol.
The compact console reference bound its uploaded bytes; the operator independently
verified and durably retained them before deleting transfer objects. The nested
six-case receipt keeps its original local-emulation schema and false native flag.
Native host observations, operator EC2 binding and cleanup evidence live in
separate records; the historical receipt was not relabelled.

The supervisor verified VM termination, volume and security-group deletion, and
transfer bucket deletion. A second read-only AWS check independently observed
the exact instance terminated and the exact volume, group and bucket absent.
There were no cleanup errors and no retry VM. See `independent-cleanup.json`,
`vm/cleanup.json`, `retention.json` and `transfer.json`.

This crosses the exact packaged QPP image's bounded native replay gate. It does
not prove hosted Marqov job submission/result admission, complete redistribution
coverage, broad circuit correctness, all CPU/GPU simulators or performance at
scale. Prior standalone library findings and original source console-recovery
limitations remain unchanged; this run has its own successful console/artifact
binding. The main agent remained active and was not messaged or interrupted.
