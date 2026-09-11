"""Fixed standalone CUDA-Q probe. A GPU is mandatory; never silently select CPU."""

import hashlib
import json
from pathlib import Path
import sys

from fixtures import SHOTS, TOLERANCE, cases, check, qasm


def main(target):
    if target not in ("nvidia", "tensornet"):
        raise ValueError("target_rejected")
    import cudaq

    if cudaq.num_available_gpus() < 1:
        raise RuntimeError("gpu_required")
    if target == "nvidia":
        cudaq.set_target(target, option="fp64")
    else:
        cudaq.set_target(target)
    if cudaq.get_target().name != target:
        raise RuntimeError("target_mismatch")
    records = []
    for case in cases():
        kernel = cudaq.make_kernel()
        qubits = kernel.qalloc(case["qubits"])
        for gate in case["gates"]:
            if gate[0] == "x":
                kernel.x(qubits[gate[1]])
            elif gate[0] == "h":
                kernel.h(qubits[gate[1]])
            elif gate[0] == "cx":
                kernel.cx(qubits[gate[1]], qubits[gate[2]])
            else:
                raise ValueError("gate_rejected")
        kernel.mz(qubits)
        cudaq.set_random_seed(42)
        counts = dict(cudaq.sample(kernel, shots_count=SHOTS).items())
        # Asymmetric endpoint vectors reject reversed logical ordering.
        check(counts, case)
        records.append(
            {
                "case": case["name"],
                "counts": counts,
                "expected": case["expected"],
                "program_sha256": hashlib.sha256(qasm(case).encode()).hexdigest(),
            }
        )
    libraries = sorted(
        {
            line.split()[-1]
            for line in Path("/proc/self/maps").read_text().splitlines()
            if "/" in line
            and any(
                s in line.lower()
                for s in ("libnvqir", "libcustatevec", "libcutensornet")
            )
        }
    )
    required = "libcustatevec" if target == "nvidia" else "libcutensornet"
    if not any(required in path for path in libraries):
        raise RuntimeError("gpu_library_evidence_missing")
    print(
        "QB_GPU_RESULT "
        + json.dumps(
            {
                "scope": "standalone upstream CUDA-Q, not Qristal Core integration",
                "target": target,
                "cudaq_version": cudaq.__version__,
                "gpu_count": cudaq.num_available_gpus(),
                "shots": SHOTS,
                "tolerance": TOLERANCE,
                "libraries": libraries,
                "records": records,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
