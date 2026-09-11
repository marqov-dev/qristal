"""Standalone isolated-workload adapter; never an admission or result authority."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

IMAGE = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"
VERSION = "qristal.cudaq-workload/v1"
MAX_BYTES = 16384


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def parse(raw, digest):
    if (
        not re.fullmatch("[a-f0-9]{64}", digest)
        or hashlib.sha256(raw).hexdigest() != digest
    ):
        raise ValueError("artifact_digest")
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("artifact_size")
    data = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
    )
    fields = {"schema", "target", "qubits", "shots", "seed", "gates"}
    if type(data) is not dict or set(data) != fields:
        raise ValueError("artifact_fields")
    if data["schema"] != "qristal.cudaq-circuit/v1" or data["target"] not in (
        "nvidia",
        "tensornet",
    ):
        raise ValueError("artifact_profile")
    if not (
        integer(data["qubits"], 1, 12)
        and integer(data["shots"], 1, 16384)
        and integer(data["seed"], 0, 2**31 - 1)
    ):
        raise ValueError("artifact_bounds")
    if type(data["gates"]) is not list or not 1 <= len(data["gates"]) <= 256:
        raise ValueError("gate_bounds")
    for gate in data["gates"]:
        if type(gate) is not list or not gate or type(gate[0]) is not str:
            raise ValueError("gate_shape")
        arity = {"x": 1, "h": 1, "cx": 2}.get(gate[0])
        if (
            arity is None
            or len(gate) != arity + 1
            or not all(integer(q, 0, data["qubits"] - 1) for q in gate[1:])
            or len(set(gate[1:])) != arity
        ):
            raise ValueError("gate_rejected")
    return data


def read_artifact(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("regular_artifact_required")
        return stream.read(MAX_BYTES + 1)


def libraries():
    return sorted(
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


def execute(raw, digest):
    data = parse(raw, digest)  # Validate before importing/initializing the GPU runtime.
    import cudaq

    if cudaq.num_available_gpus() < 1:
        raise RuntimeError("gpu_required")
    target = data["target"]
    cudaq.set_target(target, **({"option": "fp64"} if target == "nvidia" else {}))
    if cudaq.get_target().name != target:
        raise RuntimeError("target_mismatch")
    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(data["qubits"])
    for gate in data["gates"]:
        if gate[0] == "x":
            kernel.x(qubits[gate[1]])
        elif gate[0] == "h":
            kernel.h(qubits[gate[1]])
        else:
            kernel.cx(qubits[gate[1]], qubits[gate[2]])
    kernel.mz(qubits)
    cudaq.set_random_seed(data["seed"])
    counts = dict(cudaq.sample(kernel, shots_count=data["shots"]).items())
    if (
        not counts
        or any(
            type(k) is not str
            or len(k) != data["qubits"]
            or not set(k) <= {"0", "1"}
            or type(v) is not int
            or v <= 0
            for k, v in counts.items()
        )
        or sum(counts.values()) != data["shots"]
    ):
        raise RuntimeError("counts_rejected")
    loaded = libraries()
    required = (
        ("libnvqir-cusvsim-fp64.so", "libcustatevec")
        if target == "nvidia"
        else ("libnvqir-tensornet.so", "libcutensornet")
    )
    if not all(any(name in lib for lib in loaded) for name in required):
        raise RuntimeError("gpu_library_evidence")
    return dict(
        schema="qristal.cudaq-candidate/v1",
        adapter=VERSION,
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256=digest,
        runtime_image=IMAGE,
        target=target,
        cudaq_version=cudaq.__version__,
        libraries=loaded,
        gpu_count=cudaq.num_available_gpus(),
        qubits=data["qubits"],
        shots=data["shots"],
        seed=data["seed"],
        bit_order="logical-qubit-zero-first",
        counts=counts,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        result = execute(read_artifact(args.artifact), args.sha256)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    except Exception:
        # Do not reflect arbitrary input/runtime diagnostics into a result candidate.
        print("GPU workload failed; no candidate result", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
