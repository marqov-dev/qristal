"""Fixed cross-runtime correctness vectors, not performance or scale qualification."""

import math

SHOTS = 16384
TOLERANCE = 0.025


def cases():
    return [
        {"name": "x-first", "qubits": 3, "gates": [("x", 0)], "expected": {"100": 1}},
        {"name": "x-last", "qubits": 3, "gates": [("x", 2)], "expected": {"001": 1}},
        {
            "name": "interference",
            "qubits": 3,
            "gates": [("h", 0), ("h", 0)],
            "expected": {"000": 1},
        },
        {
            "name": "bell",
            "qubits": 2,
            "gates": [("h", 0), ("cx", 0, 1)],
            "expected": {"00": 0.5, "11": 0.5},
        },
        {
            "name": "ghz8",
            "qubits": 8,
            "gates": [("h", 0)] + [("cx", 0, i) for i in range(1, 8)],
            "expected": {"0" * 8: 0.5, "1" * 8: 0.5},
        },
        {
            "name": "inverse-ghz",
            "qubits": 4,
            "gates": [("h", 0)]
            + [("cx", 0, i) for i in range(1, 4)]
            + [("cx", 0, i) for i in range(3, 0, -1)]
            + [("h", 0)],
            "expected": {"0000": 1},
        },
    ]


def qasm(case):
    n = case["qubits"]
    gates = "\n".join(
        g[0] + " " + ",".join(f"q[{i}]" for i in g[1:]) + ";" for g in case["gates"]
    )
    return f'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[{n}];\ncreg c[{n}];\n{gates}\nmeasure q -> c;\n'


def check(counts, case):
    expected = case["expected"]
    if (
        type(counts) is not dict
        or not counts
        or not set(counts) <= set(expected)
        or any(type(v) is not int or v <= 0 for v in counts.values())
        or sum(counts.values()) != SHOTS
    ):
        raise ValueError("counts_rejected")
    for bits, probability in expected.items():
        if not math.isfinite(probability) or abs(
            counts.get(bits, 0) / SHOTS - probability
        ) > (0 if probability in (0, 1) else TOLERANCE):
            raise ValueError("probability_rejected")
