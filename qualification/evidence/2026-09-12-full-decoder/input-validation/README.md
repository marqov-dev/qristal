# Native Release input validation

Three GoogleTest cases passed with `-O1 -DNDEBUG`: missing/wrong types,
10 malformed tables, and two accepted normalized tables. The tests compiled
`quantum_decoder.cpp` directly against installed XACC and cached GoogleTest;
no installed plugin was replaced. Decoder source revision:
`ac2ad4113a12e06fb363845ffb65b1d331d44ed7`.

The 180-second compile-and-test container completed with exit 0 and its removal
was verified. This is initialization coverage, not full algorithm correctness,
complete register safety, CMake integration validation or a rebuilt runtime image.
The command and source hash are recorded. The harness used an uncommitted
variant of the baseline probe (now retained as `input_probe.py`); the recorded
qualification source revision identifies its baseline, not a committed harness.
