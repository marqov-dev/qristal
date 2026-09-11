"""Offline mapping experiment. Returns display data, never an accepted receipt."""

from dataclasses import dataclass
import hashlib
import json
import re


@dataclass(frozen=True)
class Expectations:
    input_sha256: str
    adapter_sha256: str
    runtime_image: str
    cudaq_version: str
    target: str
    qubits: int
    shots: int
    seed: int
    libraries: tuple[str, ...]
    positions: tuple[str, ...]


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def bounded_json(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError("payload_size")

    def reject(_):
        raise ValueError("nonfinite")

    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject
        )
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("payload_encoding") from exc


def int_between(value, low, high):
    return type(value) is int and low <= value <= high


def validate(candidate_bytes, input_bytes, expected):
    if type(expected) is not Expectations:
        raise ValueError("expected_context")
    if (
        not int_between(expected.qubits, 1, 12)
        or not int_between(expected.shots, 1, 16384)
        or not int_between(expected.seed, 0, 2**31 - 1)
        or expected.target not in ("nvidia", "tensornet")
        or expected.positions != tuple(f"q[{i}]" for i in range(expected.qubits))
        or not re.fullmatch("[a-f0-9]{64}", expected.input_sha256)
        or not re.fullmatch("[a-f0-9]{64}", expected.adapter_sha256)
    ):
        raise ValueError("expected_context")
    required_library = (
        "libnvqir-cusvsim-fp64.so"
        if expected.target == "nvidia"
        else "libnvqir-tensornet.so"
    )
    if (
        type(expected.libraries) is not tuple
        or not expected.libraries
        or any(type(lib) is not str for lib in expected.libraries)
        or not any(required_library in lib for lib in expected.libraries)
        or type(expected.runtime_image) is not str
        or re.fullmatch(
            r"nvcr\.io/nvidia/quantum/cuda-quantum@sha256:[a-f0-9]{64}",
            expected.runtime_image,
        )
        is None
        or type(expected.cudaq_version) is not str
        or not expected.cudaq_version
    ):
        raise ValueError("expected_runtime")
    artifact = bounded_json(input_bytes, 16384)
    if hashlib.sha256(input_bytes).hexdigest() != expected.input_sha256:
        raise ValueError("input_binding")
    if (
        type(artifact) is not dict
        or set(artifact) != {"schema", "target", "qubits", "shots", "seed", "gates"}
        or artifact["schema"] != "qristal.cudaq-circuit/v1"
    ):
        raise ValueError("input_shape")
    for key in ("target", "qubits", "shots", "seed"):
        value = artifact[key]
        if type(value) is not type(getattr(expected, key)) or value != getattr(
            expected, key
        ):
            raise ValueError("input_placement")
    gates = artifact["gates"]
    if type(gates) is not list or not 1 <= len(gates) <= 256:
        raise ValueError("input_gates")
    for gate in gates:
        if type(gate) is not list or not gate or type(gate[0]) is not str:
            raise ValueError("input_gates")
        arity = {"x": 1, "h": 1, "cx": 2}.get(gate[0])
        if (
            arity is None
            or len(gate) != arity + 1
            or not all(int_between(q, 0, expected.qubits - 1) for q in gate[1:])
            or len(set(gate[1:])) != arity
        ):
            raise ValueError("input_gates")
    # Structural checks do not supply source admission or prove circuit execution.
    candidate = bounded_json(candidate_bytes, 131072)
    keys = {
        "schema",
        "adapter",
        "adapter_sha256",
        "input_sha256",
        "runtime_image",
        "target",
        "cudaq_version",
        "libraries",
        "gpu_count",
        "qubits",
        "shots",
        "seed",
        "bit_order",
        "counts",
    }
    if type(candidate) is not dict or set(candidate) != keys:
        raise ValueError("candidate_shape")
    constants = dict(
        schema="qristal.cudaq-candidate/v1",
        adapter="qristal.cudaq-workload/v1",
        bit_order="logical-qubit-zero-first",
        gpu_count=1,
    )
    for key, value in constants.items():
        if type(candidate[key]) is not type(value) or candidate[key] != value:
            raise ValueError("candidate_profile")
    for key in (
        "input_sha256",
        "adapter_sha256",
        "runtime_image",
        "cudaq_version",
        "target",
        "qubits",
        "shots",
        "seed",
    ):
        value = getattr(expected, key)
        if type(candidate[key]) is not type(value) or candidate[key] != value:
            raise ValueError("candidate_binding")
    if type(candidate["libraries"]) is not list or candidate["libraries"] != list(
        expected.libraries
    ):
        raise ValueError("library_binding")
    counts = candidate["counts"]
    if (
        type(counts) is not dict
        or not 1 <= len(counts) <= 2**expected.qubits
        or any(
            type(k) is not str
            or len(k) != expected.qubits
            or not set(k) <= {"0", "1"}
            or not int_between(v, 1, expected.shots)
            for k, v in counts.items()
        )
        or sum(counts.values()) != expected.shots
    ):
        raise ValueError("counts_rejected")
    return dict(
        scope="offline-display-preview; unaccepted",
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        input_sha256=expected.input_sha256,
        target=expected.target,
        positions=list(expected.positions),
        counts=dict(sorted(counts.items())),
        shots=dict(
            requested=expected.shots, successful=expected.shots, discarded=0, unknown=0
        ),
    )
