"""Independent calibration and held-out readout correction; public CPU simulation."""
import hashlib
import json
import math

SHOTS = 16384
POINTS = ((0.05, 0.10), (0.20, 0.10), (0.40, 0.40), (0.50, 0.50))
RAW_TOLERANCE = 0.025
CORRECTED_TOLERANCE = 0.08
MIN_DETERMINANT = 0.10
MIN_RELATIVE_IMPROVEMENT = 0.50
BITS = ("00", "01", "10", "11")
HEADER = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; '
FIXTURES = {
    "zero": ("", {"00": 1.0}),
    "x0": ("x q[0]; ", {"10": 1.0}),
    "x1": ("x q[1]; ", {"01": 1.0}),
    "both": ("x q[0]; x q[1]; ", {"11": 1.0}),
    "h0": ("h q[0]; ", {"00": 0.5, "10": 0.5}),
    "bell": ("h q[0]; cx q[0],q[1]; ", {"00": 0.5, "11": 0.5}),
}


def schedule():
    result = []
    for setting, (p10, p01) in enumerate(POINTS):
        cases = [("calibration", "zero"), ("calibration", "x0")]
        if setting < 3:
            cases += [("held_out", name) for name in FIXTURES]
        for index, (role, name) in enumerate(cases):
            result.append({
                "id": f"{setting}:{role}:{name}", "setting": setting,
                "role": role, "fixture": name,
                "program": HEADER + FIXTURES[name][0] + "measure q -> c;",
                "options": {"qubits": 2, "shots": SHOTS,
                            "seed": 12001 + setting * 100 + index,
                            "readout": {"p10": p10, "p01": p01}},
            })
    return result


def distribution(counts):
    if (not isinstance(counts, dict) or not counts or not set(counts) <= set(BITS)
            or any(type(n) is not int or n <= 0 for n in counts.values())
            or sum(counts.values()) != SHOTS):
        raise ValueError("counts")
    return {bits: counts.get(bits, 0) / SHOTS for bits in BITS}


def calibrate(zero_counts, one_counts):
    """Only measured calibration samples enter this estimator."""
    zero, one = distribution(zero_counts), distribution(one_counts)
    if zero["01"] + zero["11"] + one["01"] + one["11"] != 0:
        raise ValueError("calibration_q1")
    a, b = zero["10"], one["00"]
    determinant = 1 - a - b
    if determinant < MIN_DETERMINANT:
        raise ValueError("calibration_rejected")
    return {"p10_hat": a, "p01_hat": b, "determinant": determinant,
            "variance_p10": a * (1 - a) / SHOTS,
            "variance_p01": b * (1 - b) / SHOTS}


def correct(counts, calibration):
    """Inverse assignment matrix on q0; preserve signed quasi-probabilities."""
    observed = distribution(counts)
    a, b, d = (calibration[k] for k in ("p10_hat", "p01_hat", "determinant"))
    if not all(math.isfinite(x) for x in (a, b, d)) or d < MIN_DETERMINANT:
        raise ValueError("calibration_rejected")
    result = {}
    for q1 in ("0", "1"):
        y0, y1 = observed["0" + q1], observed["1" + q1]
        result["0" + q1] = ((1 - b) * y0 - b * y1) / d
        result["1" + q1] = (-a * y0 + (1 - a) * y1) / d
    return result


def observable(probabilities, name):
    if name not in ("Z0", "Z0Z1"):
        raise ValueError("observable")
    return sum(p * (-1 if bits[0] == "1" else 1)
               * ((-1 if bits[1] == "1" else 1) if name == "Z0Z1" else 1)
               for bits, p in probabilities.items())


def uncertainty(counts, calibration, name):
    """First-order SE, including independent calibration and held-out sampling."""
    p = distribution(counts)
    corrected = observable(correct(counts, calibration), name)
    a, b, d = (calibration[k] for k in ("p10_hat", "p01_hat", "determinant"))
    t = {bits: (-1 if bits[1] == "1" else 1) if name == "Z0Z1" else 1
         for bits in BITS}
    mean_t = sum(t[bits] * p[bits] for bits in BITS)
    values = {bits: ((-1 if bits[0] == "1" else 1) - (b - a)) * t[bits]
              for bits in BITS}
    mean = sum(values[bits] * p[bits] for bits in BITS)
    second = sum(values[bits] ** 2 * p[bits] for bits in BITS)
    variance = max(0.0, second - mean ** 2) / SHOTS / d ** 2
    variance += ((mean_t + corrected) / d) ** 2 * calibration["variance_p10"]
    variance += ((corrected - mean_t) / d) ** 2 * calibration["variance_p01"]
    return math.sqrt(variance)


def forward(ideal, a, b):
    # Independent analytic forward model used for validation, never correction.
    result = dict.fromkeys(BITS, 0.0)
    for bits, p in ideal.items():
        flip = a if bits[0] == "0" else b
        result[bits] += p * (1 - flip)
        result[("1" if bits[0] == "0" else "0") + bits[1]] += p * flip
    return result


def validate(report):
    if report.get("schema") != "qb-readout-mitigation-v1":
        raise ValueError("schema")
    records = report["records"]
    expected = {item["id"]: item for item in schedule()}
    if len(records) != len(expected) or {r["id"] for r in records} != set(expected):
        raise ValueError("schedule")
    for record in records:
        item = expected[record["id"]]
        if any(record.get(key) != value for key, value in item.items()):
            raise ValueError("binding")
        if (record["program_sha256"] != hashlib.sha256(item["program"].encode()).hexdigest()
                or record["options_sha256"] != hashlib.sha256(
                    json.dumps(item["options"], sort_keys=True).encode()).hexdigest()
                or record["backend"] != "aer"):
            raise ValueError("hash_binding")
        p = distribution(record["counts"])
        ideal = FIXTURES[item["fixture"]][1]
        model = forward(ideal, *POINTS[item["setting"]])
        for bits in BITS:
            if abs(p[bits] - model[bits]) > (0 if model[bits] == 0 else RAW_TOLERANCE):
                raise ValueError("forward_model")
    return records


def analyze(report):
    records = {r["id"]: r for r in validate(report)}
    settings, outcomes = [], []
    for setting in range(4):
        zero = records[f"{setting}:calibration:zero"]
        one = records[f"{setting}:calibration:x0"]
        try:
            cal = calibrate(zero["counts"], one["counts"])
        except ValueError as error:
            if setting != 3 or str(error) != "calibration_rejected":
                raise
            settings.append({"setting": setting, "status": "rejected",
                             "reason": "determinant_below_0.10"})
            continue
        if setting == 3:
            raise ValueError("singular_control_not_rejected")
        raw_errors, corrected_errors = [], []
        for name, (_, ideal) in FIXTURES.items():
            record = records[f"{setting}:held_out:{name}"]
            p = distribution(record["counts"])
            q = correct(record["counts"], cal)
            if max(abs(q[b] - ideal.get(b, 0)) for b in BITS) > CORRECTED_TOLERANCE:
                raise ValueError("corrected_probability")
            for obs in ("Z0", "Z0Z1"):
                target = observable(ideal, obs)
                raw_value, corrected_value = observable(p, obs), observable(q, obs)
                raw_errors.append(abs(raw_value - target))
                corrected_errors.append(abs(corrected_value - target))
                outcomes.append({
                    "setting": setting, "fixture": name, "observable": obs,
                    "ideal": target, "raw": raw_value, "corrected": corrected_value,
                    "raw_se": math.sqrt(max(0, 1 - raw_value ** 2) / SHOTS),
                    "corrected_se": uncertainty(record["counts"], cal, obs),
                    "quasi_probabilities": q,
                    "negative_mass": -sum(min(0, value) for value in q.values()),
                })
        raw_mae = sum(raw_errors) / len(raw_errors)
        corrected_mae = sum(corrected_errors) / len(corrected_errors)
        improvement = 1 - corrected_mae / raw_mae
        if improvement < MIN_RELATIVE_IMPROVEMENT:
            raise ValueError("insufficient_held_out_improvement")
        settings.append({"setting": setting, "status": "corrected", "calibration": cal,
                         "raw_mean_absolute_observable_error": raw_mae,
                         "corrected_mean_absolute_observable_error": corrected_mae,
                         "relative_improvement": improvement})
    return {"settings": settings, "outcomes": outcomes}


def main():
    from local_pipeline import run_readout

    records = []
    for item in schedule():
        program = item["program"].encode()
        options = json.dumps(item["options"], sort_keys=True).encode()
        result = run_readout(program, options)
        if result.result.program_sha256 != result.canonical_program_sha256:
            raise ValueError("canonical_binding")
        records.append({**item, "program_sha256": result.original_program_sha256,
                        "options_sha256": result.options_sha256,
                        "backend": result.result.backend, "counts": dict(result.result.counts)})
    report = {"schema": "qb-readout-mitigation-v1", "records": records}
    analyze(report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
