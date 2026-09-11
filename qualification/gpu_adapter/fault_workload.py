"""Fixed qualification fixture, never a user-selectable adapter operation."""

import hashlib
import json
from pathlib import Path
import sys
import time
from adapter import execute

raw = json.dumps(
    dict(
        schema="qristal.cudaq-circuit/v1",
        target="nvidia",
        qubits=3,
        shots=17,
        seed=42,
        gates=[["x", 0]],
    )
).encode()
execute(raw, hashlib.sha256(raw).hexdigest())
Path("/tmp/gpu-ready").write_text("ready")
if sys.argv[1] == "overflow":
    while not Path("/tmp/go").exists():
        time.sleep(0.1)
    while True:
        sys.stdout.write("x" * 1024 + "\n")
        sys.stdout.flush()
        time.sleep(0.001)
else:
    while True:
        time.sleep(1)
