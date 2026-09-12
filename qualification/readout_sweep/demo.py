"""Fixed Bell readout sweep: public CPU Aer, not hardware calibration."""

import hashlib
import json

POINTS = (0, 0.05, 0.10, 0.20, 0.40)
SEEDS = (7, 42)
SHOTS = 16384
TOLERANCE = 0.025
PROGRAM = b'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q -> c;'


def probabilities(p10, p01):
    # Output order is q[0],q[1]. Error acts only on q[0].
    return {"00": (1 - p10) / 2, "10": p10 / 2, "01": p01 / 2, "11": (1 - p01) / 2}


def validate(report):
    if report.get("shots") != SHOTS or report.get("absolute_tolerance") != TOLERANCE:
        raise ValueError("sweep_profile")
    expected_keys = {
        (seed, p10, p01) for seed in SEEDS for p10 in POINTS for p01 in POINTS
    }
    seen = set()
    for record in report["records"]:
        options = record["options"]
        key = (options["seed"], options["readout"]["p10"], options["readout"]["p01"])
        if key not in expected_keys or key in seen:
            raise ValueError("sweep_grid")
        seen.add(key)
        raw_options = json.dumps(options, sort_keys=True).encode()
        if (
            options["shots"] != SHOTS
            or options["qubits"] != 2
            or record["program"] != PROGRAM.decode()
            or record["program_sha256"] != hashlib.sha256(PROGRAM).hexdigest()
            or record["options_sha256"] != hashlib.sha256(raw_options).hexdigest()
            or record["backend"] != "aer"
        ):
            raise ValueError("sweep_binding")
        counts = record["counts"]
        expected = probabilities(key[1], key[2])
        if not set(counts) <= set(expected) or sum(counts.values()) != SHOTS:
            raise ValueError("sweep_counts")
        if any(type(n) is not int or n <= 0 for n in counts.values()):
            raise ValueError("sweep_counts")
        for bits, probability in expected.items():
            tolerance = 0 if probability == 0 else TOLERANCE
            if abs(counts.get(bits, 0) / SHOTS - probability) > tolerance:
                raise ValueError("sweep_probability")
    if seen != expected_keys:
        raise ValueError("sweep_incomplete")


def main():
    from local_pipeline import run_readout

    records = []
    for seed in SEEDS:
        for p10 in POINTS:
            for p01 in POINTS:
                options = {
                    "qubits": 2,
                    "shots": SHOTS,
                    "seed": seed,
                    "readout": {"p10": p10, "p01": p01},
                }
                raw = json.dumps(options, sort_keys=True).encode()
                observed = run_readout(PROGRAM, raw)
                if observed.result.program_sha256 != observed.canonical_program_sha256:
                    raise ValueError("canonical_binding")
                records.append(
                    {
                        "program": PROGRAM.decode(),
                        "options": options,
                        "program_sha256": observed.original_program_sha256,
                        "canonical_sha256": observed.canonical_program_sha256,
                        "options_sha256": observed.options_sha256,
                        "backend": observed.result.backend,
                        "counts": dict(observed.result.counts),
                    }
                )
    report = {
        "shots": SHOTS,
        "absolute_tolerance": TOLERANCE,
        "scope": "saved CPU Aer simulation; no hardware, commercial or hosted execution claim",
        "records": records,
    }
    validate(report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
