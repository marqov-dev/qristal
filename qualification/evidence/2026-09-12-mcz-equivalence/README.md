# Controlled-Z prototype equivalence — native subset passed

The corrected prototype at acbf69de3c7a8548919129d04826c1c8fe277f67 passed 42 QPP
complex-state fixtures, 158 sparse-sim interference fixtures and 10 rejected-input
checks. Every positive circuit ran twice on the exact same IR object. Independent
Python replay finds maximum complex-amplitude error 3.2987125042640323e-16 against
the fixed 1e-10 bound. All sparse observations match the exact deterministic
bitstring at 64 shots, including eight 18-control cases.

The first attempt at af426fd compiled but failed clone_lost_disabled before phase
or sparse execution. Our prototype inherited Circuit's child-only enable/disable
and Instruction's always-true isEnabled. Explicit enabled-state overrides fixed
this. Original failure and cleanup are in attempts/initial; do not claim a first
attempt pass or an upstream simulator defect.

The successful prototype demonstrates direct controlled-Z metadata, explicit
cloning, empty-block inversion, nested traversal, selected full-register reversals,
visitor restoration and primitive fallback equivalence. The fallback is explicitly
flattened before simulation so the simulator cannot bypass it using metadata.
This is not qualification of another backend merely because its fallback compiled.

The QPP inputs are phase-rich product states over six layouts at 2–5 qubits.
They are not an exhaustive matrix-element/unitary proof. In particular, the selected
full-register reversals leave each tested MCZ active-bit set invariant; this weakens
mapping coverage. Add a non-invariant active-set layout before claiming general
mapping support. The pending full Decoder probe does not call mapBits. Generic
flattening/serialization and bit-count APIs remain outside the prototype scope.

Both separate VMs and their exact disks, groups and private transfer resources
cleaned automatically, within their original bounds. All records retain public
source, binary and loaded runtime library identities. Installed dependency binaries
are reused, not inferred rebuilt from current Core/Decoder source revisions.

Replay with `python3 -B qualification/full_decoder/cloud/analyze_mcz.py
qualification/evidence/2026-09-12-mcz-equivalence` (one shell line). The analyzer
rechecks console binding, fixture inventories, all complex values, deterministic
counts and exact cleanup. The report's self-reported pass marker alone is insufficient.

This is qualification-only code. Full Decoder execution, supported distribution,
installed image promotion and hosted admission are separate gates in platform #2173.
