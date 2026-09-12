# Native public QFT/IQFT qualification and Decoder trace

12 September 2026. Protocol/source revision
`10c8005b623a0065a4b4de510d56922c67eae81f`, after merged Qristal PR24 at
`900dabfbe36d12549af2d034bfab5dadfc49d166`. Public XACC, Core and Decoder source
revisions and hashes are retained in `result.json`. No upstream algorithm source
changed for this experiment.

**All 70 phase-sensitive QFT cases passed**, using installed QPP and the
qualification-only provider compiled from unchanged public XACC QFT/IQFT.
Every basis input at one, two and three qubits ran through five modes. This is
native state-vector evidence, not a sampling-count or hardware experiment.

| Mode | Cases | Independently replayed maximum complex-amplitude error |
|---|---:|---:|
| Basis / index convention | 14 | 0 |
| QFT vs positive Fourier matrix | 14 | 2.36836×10^-8 |
| IQFT vs negative Fourier matrix | 14 | 2.36836×10^-8 |
| QFT followed by IQFT | 14 | 4.47199×10^-16 |
| IQFT followed by QFT | 14 | 4.45821×10^-16 |

The exact complex vectors are in `qft-vectors.json`; `analysis.json` comes from
independent Python matrix replay with the predeclared 1e-6 Fourier and 1e-10
basis/round-trip/normalization bounds. No fitted phase or post-result tolerance
change was used. XACC's QPP adapter presents q0 as the least significant bit;
basis-only fixtures verify that convention. Fourier differences are consistent
with the upstream seven-digit π literal, without claiming this is the sole error
source or a general numerical-accuracy bound.

The report records the mapped QFT provider and rebuilt Core library. The QFT
provider file hash matches the built binary:
`6e72940cf46944f5e78dbd5e36b5effed1608d3e9e7facfb44fe22df6c0dd2dc`.
This is an operator-owned observation, not external runtime attestation or
qualification of the complete XACC generators distribution.

All six Decoder initialization tests also passed. The unchanged 24-qubit,
four-trial tiny Decoder fixture again timed out at 60 seconds. This time bounded
partial output survived: XACC initializes, qft/iqft are present, backend/algorithm
checks pass, Decoder initializes, then execution reaches exponential-search
iteration 1. No measurement, improving candidate or completed caller-result
contract was retained. Full Decoder correctness remains unqualified.

The [source audit](../../full_decoder/cloud/SEARCH-HOTSPOT.md) identifies eager
many-controlled-Z decomposition as one testable cost hypothesis; it is not yet
a measured root cause. A trace-only Core probe with unchanged limits is the next
bounded task, before any optimization.

One m7i.large ran under the predeclared limits. Observation and cleanup completed
automatically: exact instance terminated, recorded disk and security group absent,
private transfer bucket/object deleted and absence verified. Resource IDs and
original deadlines are retained. There was no replacement launch, shared Docker
work, runtime source-lock promotion or hosted enablement.

Reproduce the offline analysis from the repository root:

```sh
python3 -B qualification/full_decoder/cloud/analyze_qft.py qualification/evidence/2026-09-12-qft-states
```

The analyzer rechecks console checksum, all complex vectors, library identity
and exact cleanup records. It does not launch compute or mark Decoder complete.
These fixtures establish a maintained public QFT subset and a more precise
Decoder diagnostic; existing CPU/noise, simplified Decoder and GPU evidence
remain separate.
