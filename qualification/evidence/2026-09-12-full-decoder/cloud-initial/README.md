# First isolated CPU VM — native initialization passed, bundle loading failed

12 September 2026. One Ubuntu 22.04 m7i.large ran independently of shared Docker.
Archive SHA256: `956944fccb214d84848400e258f9dae642135b37a61f1778c49303d905e2afde`.
Core merged source: `bd3a8e2808562bcd65d3e2bb9d03a970a8517d7a`.
Decoder merged source: `a58df0cf7eff0c6002aa3fed27ae6b18fdcea036`.
Guest/packer revision: `fa1e99f1232c0162467af0311ed1937c1c3103fa`.
The launcher revision is retained in `recovery.json`.

| Stage | Native observation |
|---|---|
| Rebuild Core search plugin | Compile/link exit 0; binary hash retained |
| Compile current Decoder initialization tests | Exit 0 |
| Six named initialization tests | All passed, including backend ownership and failed-initialization invalidation |
| Compile tiny caller-result executable | Exit 0 |
| Tiny execution | Exit 255 during XACC registry initialization; no simulation/result-contract observation |

The compiler output was valid ELF, but it lacked the zip resource bundle appended
by the original CMake post-build rule. XACC logged `Could not init zip archive for
bundle`, then reported sparse-sim absent from its failed registry. The latter is
not evidence of an unavailable public sparse simulator. The new qualification
harness omitted a packaging step; this is not attributed to the Decoder fixes.
The separately declared [bundle follow-up](../../../full_decoder/cloud/BUNDLE-FOLLOWUP.md)
adds the original resource-compiler command and mapped-library identity checking.

`result.json` contains the decoded observation. `console-filtered.json` and
`recovered.json` retain the checksummed console provenance. Source hashes,
compiler arguments and binary hashes are in the report. Dependencies were reused
from prior public-source builds; this was not a fresh dependency rebuild.
Only bounded output was retained; raw bootstrap and signed transfer URLs were not.

Cleanup initially stopped on `ValueError:instance_ownership` during termination.
The transfer bucket/object were already deleted. A read of the exact previously
bound instance showed it terminated, with the original client token and no subnet
field. Resuming the **unchanged** supervisor on that same instance verified its
exact disk and group absent within the original deadline. No replacement launch
or deadline extension occurred. `transfer-initial.json` preserves the first
cleanup error; `cleanup.json` and `recovery.json` record the successful recovery.
This was not first-attempt unattended cleanup.

The six native tests exercise initialization against linked XACC with a recording
backend stub; they do not execute the full algorithm. No installed Decoder plugin,
runtime source lock, image or hosted capability was promoted.
