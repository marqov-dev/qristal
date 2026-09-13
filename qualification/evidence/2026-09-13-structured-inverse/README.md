# Controlled inverse candidate: small correctness gate passed

After PR28 merged at `66e21433a18ef0361d859614ff5bbea5e2ec448a`, three independent
CPU VM experiments qualified a narrow inverse candidate and exposed backend
compatibility/phase assumptions. Final native source:
`97b2cbca255ee50982a20e2d56f9dcc54fa0e2b9`. Exact Core, Decoder and XACC revisions
are retained in result.json. Installed runtime libraries were reused, not rebuilt
from those repository heads; loaded library and executable hashes are retained.

| Evidence | Result | Limit |
|---|---|---|
| Candidate QPP complex states | 140 cases passed, each exact lowered IR executed twice | Two layouts, one/two controls; X/Y/Z/H and signed Rx/Ry/Rz |
| Independent Python vectors | 20 candidate vectors passed; max absolute error 1.7554e-16 | Native matrix checks cover the other candidate modes; their vectors are not retained |
| Legacy primitive fallback | 20 vectors retained; 16 match, 4 controlled-Rx phase discrepancies | Failed exact-phase cases are not counted as candidate passes |
| Direct sparse inverse interference | 20 cases passed at 16,384 shots; max probability residual 0.009878 | Fixed 0.025 absolute outcome bound; no fixed sparse RNG seed claimed |
| Sparse roundtrip | 20 cases, each IR twice, exactly 64 zero outcomes | Roundtrip alone is insufficient; inverse-only interference is separate |
| Rejections | 12 malformed/unsupported cases passed | Not exhaustive public API validation |

Candidate modes include direct inverse, populated controlled-block metadata,
roundtrip, clone, disabled clone, active-set-changing bit mapping and nested
inverse order. The helper preserves supported metadata and rejects unsupported
leaves; it deliberately cannot yet invert the entire Decoder preparation.
QPP uses an explicit phase-preserving parity decomposition for rotations and
controlled-X basis conjugation for H. Sparse receives direct metadata. This QPP
lowering is currently part of the qualification consumer, not an installed public
adapter or generic backend dispatch guard. It is capped at two controls.

## What the failures taught us

1. `attempts/initial` (bf95ddb): compiled and passed input rejection; failed the
   first nested Ry case. Our prototype assumed QPP supported all direct controls
   accepted by sparse-sim. The selected QPP visitor only shortcuts X/Y/Z; empty
   unsupported metadata silently has no leaves to execute.
2. `attempts/qpp-legacy-lowering` (1936671): explicit use of the installed C-U
   decomposition passed X/Y/Z/H, then failed controlled Rx inversion. Complex
   error was 0.282897. The final run retains legacy fallback vectors instead of
   treating that decomposition as an automatically correct reference.
3. Final 97b2cbc: explicit candidate lowering passed the unchanged 1e-10 matrix
   tolerance, plus direct sparse checks. No process/time/tolerance enlargement.

The four legacy discrepancies are Rx(+/-0.37) inverses with one and two controls.
One-control outputs have phase +pi/4, two-control outputs +pi/8 relative to the
reference. Diagnostic phase-aligned errors are below 3.2e-16, so these are global
phase differences in the tested standalone circuits; their probabilities are
unchanged. Phase alignment is diagnostic only, not used to pass the exact-phase
gate. A phase can become relative under an additional control, but that harmful
composition has **not** been demonstrated here. Do not claim these four cases
prove a wrong decoded answer or a flaw in every upstream release.

The source audit identifies an Rz-versus-U1 substitution in the selected XACC
controlled-U builder as a plausible explanation. See the
[preparation audit](../../full_decoder/cloud/PREPARATION-AUDIT.md). The exact
legacy installed binary has not been repaired or promoted.

## What remains

The full Decoder was not rerun in this batch; its previous four-trial caller
fixture still lacks completion. There is no measured speedup from these small
checks. Forward preparation and inverse have similar visitor counts but markedly
different costs: inventory the actual nested preparation and state work before
choosing a performance change. Broader primitive gates, more controls, generic IR
serialization, backend admission, caller/oracle and stochastic results, and exact
installed-image qualification remain open. Existing CPU/noise and standalone GPU
conference demonstrations are separate from this research result.

All three exact instances, disks, groups and transfer resources cleaned
automatically. Public infrastructure IDs are consistently anonymized; original
local run audits retain the provider identifiers. Simulator payloads and their
checksums are unchanged. Shared platform/SDK repositories and the main release
agent were untouched. No production Core, runtime lock or hosted route changed.

Replay: `python3 -B qualification/full_decoder/cloud/analyze_inverse.py qualification/evidence/2026-09-13-structured-inverse`.
[Protocol and attempt history](../../full_decoder/cloud/INVERSE-PRESERVATION-PROTOCOL.md).
