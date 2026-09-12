import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mitigation_demo", HERE / "demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def counts(probabilities):
    result = {key: int(value * demo.SHOTS) for key, value in probabilities.items()}
    key = max(probabilities, key=probabilities.get)
    result[key] += demo.SHOTS - sum(result.values())
    return {key: value for key, value in result.items() if value}


def synthetic_report():
    records = []
    for item in demo.schedule():
        p = demo.forward(demo.FIXTURES[item["fixture"]][1], *demo.POINTS[item["setting"]])
        records.append({**item, "counts": counts(p), "backend": "aer",
                        "program_sha256": hashlib.sha256(item["program"].encode()).hexdigest(),
                        "options_sha256": hashlib.sha256(json.dumps(
                            item["options"], sort_keys=True).encode()).hexdigest()})
    return {"schema": "qb-readout-mitigation-v1", "records": records}


class Mitigation(unittest.TestCase):
    def test_exact_assignment_inverse_and_q0_order(self):
        zero, one = counts({"00": .75, "10": .25}), counts({"00": .125, "10": .875})
        calibration = demo.calibrate(zero, one)
        for ideal in demo.FIXTURES.values():
            observed = counts(demo.forward(ideal[1], .25, .125))
            corrected = demo.correct(observed, calibration)
            for bits in demo.BITS:
                self.assertAlmostEqual(corrected[bits], ideal[1].get(bits, 0))

    def test_distinct_calibration_and_held_out_seeds(self):
        schedule = demo.schedule()
        self.assertEqual(len(schedule), 26)
        self.assertEqual(len({item["options"]["seed"] for item in schedule}), 26)

    def test_singular_matrix_rejected(self):
        ambiguous = {"00": 8192, "10": 8192}
        with self.assertRaisesRegex(ValueError, "calibration_rejected"):
            demo.calibrate(ambiguous, ambiguous)

    def test_negative_quasi_probabilities_are_not_clipped(self):
        cal = demo.calibrate(counts({"00": .75, "10": .25}),
                             counts({"00": .125, "10": .875}))
        q = demo.correct({"00": demo.SHOTS}, cal)
        self.assertLess(q["10"], 0)
        self.assertGreater(q["00"], 1)
        self.assertAlmostEqual(sum(q.values()), 1)

    def test_calibration_uncertainty_is_included(self):
        cal = demo.calibrate(counts({"00": .75, "10": .25}),
                             counts({"00": .125, "10": .875}))
        sample = counts(demo.forward(demo.FIXTURES["bell"][1], .25, .125))
        full = demo.uncertainty(sample, cal, "Z0Z1")
        no_calibration = {**cal, "variance_p10": 0, "variance_p01": 0}
        self.assertGreater(full, demo.uncertainty(sample, no_calibration, "Z0Z1"))

    def test_uncertainty_derivatives_match_finite_difference(self):
        cal = demo.calibrate(counts({"00": .75, "10": .25}),
                             counts({"00": .125, "10": .875}))
        sample = counts(demo.forward(demo.FIXTURES["bell"][1], .25, .125))
        for name in ("Z0", "Z0Z1"):
            q = demo.observable(demo.correct(sample, cal), name)
            mean_t = 1 if name == "Z0" else 0
            for key, expected in (("p10_hat", (q + mean_t) / cal["determinant"]),
                                  ("p01_hat", (q - mean_t) / cal["determinant"])):
                changed = dict(cal)
                changed[key] += 1e-7
                changed["determinant"] -= 1e-7
                derivative = (demo.observable(demo.correct(sample, changed), name) - q) / 1e-7
                self.assertAlmostEqual(derivative, expected, places=5)

    def test_profile_accepts_analytic_fixture_and_rejects_seed_reuse(self):
        report = synthetic_report()
        result = demo.analyze(report)
        self.assertEqual(result["settings"][-1]["status"], "rejected")
        self.assertEqual(len(result["outcomes"]), 36)
        changed = copy.deepcopy(report)
        changed["records"][2]["options"]["seed"] = changed["records"][0]["options"]["seed"]
        with self.assertRaisesRegex(ValueError, "binding"):
            demo.analyze(changed)

    def test_missing_or_changed_count_record_rejected(self):
        report = synthetic_report()
        with self.assertRaisesRegex(ValueError, "schedule"):
            demo.analyze({**report, "records": report["records"][:-1]})
        report["records"][0]["counts"] = {"00": demo.SHOTS}
        with self.assertRaisesRegex(ValueError, "forward_model"):
            demo.analyze(report)

    def test_calibration_requires_preserved_second_qubit(self):
        with self.assertRaisesRegex(ValueError, "calibration_q1"):
            demo.calibrate({"01": demo.SHOTS}, {"10": demo.SHOTS})


if __name__ == "__main__":
    unittest.main()
