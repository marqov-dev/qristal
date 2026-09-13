# Further-control phase test and preparation inventory

After PR29 merge, one bounded CPU VM reuses the selected installed runtime. The
standalone composition consumer tests Rx angles ±0.37 and ±0.9. Qubits: inner
control 0 prepared 1, target 1 prepared 0, outer control 2 prepared +.

Candidate route applies a two-control Rx(-angle) through the previously qualified
parity lowering, then two-control Rx(+angle), then H on the outer control.
Outer-one probability must be <1e-20 (squared amplitude scale of the existing
1e-10 complex bound). Every exact IR runs twice.

Legacy route constructs the installed primitive inverse of one-control Rx,
places an additional control around that compiled circuit using the installed
C-U builder, and forces its primitive leaves to execute. It then applies the
same candidate ideal uncomputation and outer H. Retain full complex vectors and
outer-one probabilities for all four angles. These are diagnostic observations,
not assumed passes. This tests control of compiled IR, not just supplying two
controls to original gate metadata; those are distinct composition routes.

The separate inventory consumer runs the unchanged tiny fixture setup with a
hash-bound Decoder source insertion immediately after preparation construction.
It reports top-level child inventories and the legacy inverse, then intentionally
throws QB_INVENTORY_ONLY_STOP. Exit 1 is expected only alongside the exact completion
and stop markers. No exponential search, simulation or caller result is attempted.
A diagnostic public QFT provider is built using the established resource-bundle
step so preparation can be constructed. All source/library identities are retained.

Inventory counts include raw nested nodes and primitive leaves. Estimated sparse
visits skip the children of single supported controlled X/Y/Z/H/Rx/Ry/Rz blocks;
these are structural estimates, not observed gate execution or a timing benchmark.
The raw scan is bounded to one million nodes and depth 128 per reported subtree.

Compile bounds 180 s; each consumer 60 s; same owned VM resources, fixed observation
and automatic exact cleanup. Console envelope unchanged. No shared platform/SDK,
production Core/XACC, runtime source lock or hosted route change.
