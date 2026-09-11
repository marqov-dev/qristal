"""Replay retained native candidates using independent fixture expectations."""

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "accelerators"))
from fixtures import cases, check
from mapping import Expectations, validate

IMAGE = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"
ADAPTER_SHA = "d279cc23b80f1d4a8e7923891823fb14a67c083363454744b0cb605019cc9a80"
CUDAQ = "CUDA-Q Version amd64-cu12-0.15.0 (https://github.com/NVIDIA/cuda-quantum f6d1f1d50d9cd4fef60011197cafe67c9035c3dc)"


def context(target, case):
    # Construct from fixed analytic fixtures and reviewed runtime pins, never candidate fields.
    raw = json.dumps(
        dict(
            schema="qristal.cudaq-circuit/v1",
            target=target,
            qubits=case["qubits"],
            shots=16384,
            seed=42,
            gates=case["gates"],
        ),
        sort_keys=True,
    ).encode()
    libs = [
        "/opt/nvidia/cudaq/lib/libnvqir.so",
        "/usr/local/lib/python3.12/dist-packages/cuquantum/lib/libcustatevec.so.1",
        "/usr/local/lib/python3.12/dist-packages/cuquantum/lib/libcutensornet.so.2",
    ]
    if target == "nvidia":
        libs += [
            "/opt/nvidia/cudaq/lib/libnvqir-custatevec-kernels.so",
            "/opt/nvidia/cudaq/lib/libnvqir-cusvsim-fp64.so",
        ]
    else:
        libs += ["/opt/nvidia/cudaq/lib/libnvqir-tensornet.so"]
    return raw, Expectations(
        hashlib.sha256(raw).hexdigest(),
        ADAPTER_SHA,
        IMAGE,
        CUDAQ,
        target,
        case["qubits"],
        16384,
        42,
        tuple(sorted(libs)),
        tuple(f"q[{i}]" for i in range(case["qubits"])),
    )


def records():
    path = HERE.parent / "evidence/2026-09-11-gpu-adapter/result.json"
    return json.loads(path.read_text())["records"]


def replay():
    saved = records()
    result = []
    for target in ("nvidia", "tensornet"):
        for case in cases():
            matches = [
                r
                for r in saved
                if r["case"] == case["name"] and r["candidate"]["target"] == target
            ]
            if len(matches) != 1:
                raise ValueError("native_case_set")
            candidate = json.dumps(
                matches[0]["candidate"], sort_keys=True, separators=(",", ":")
            ).encode()
            raw, expected = context(target, case)
            # Labels exercise the same mapper, not actual Direct/Temporal engines.
            previews = {
                engine: validate(candidate, raw, expected)
                for engine in ("direct_v1", "temporal_v1")
            }
            if previews["direct_v1"] != previews["temporal_v1"]:
                raise ValueError("mapping_parity")
            check(previews["direct_v1"]["counts"], case)
            result.append(
                dict(
                    target=target,
                    case=case["name"],
                    preview=previews["direct_v1"],
                    synthetic_engine_parity=True,
                )
            )
    return dict(
        scope="offline replay; no new GPU runs or hosted acceptance", cases=result
    )


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
