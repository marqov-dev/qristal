import copy
import hashlib
import json
from pathlib import Path
import unittest

from demo import probabilities, validate

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-readout-sweep"


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((EVIDENCE / "result.json").read_text())

    def test_retained_native_observations_and_cleanup(self):
        validate(self.report)
        self.assertEqual(
            json.loads((EVIDENCE / "demo.stdout").read_text()), self.report
        )
        manifest = json.loads((EVIDENCE / "manifest.json").read_text())
        for name, expected in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest(), expected
            )
        self.assertIs(
            json.loads((EVIDENCE / "demo-cleanup.json").read_text())["absent"], True
        )
        self.assertEqual(
            hashlib.sha256(
                (Path(__file__).parent / "demo.py").read_bytes()
            ).hexdigest(),
            manifest["sources"]["readout_demo.py"],
        )

    def test_asymmetric_analytic_anchor(self):
        self.assertEqual(
            probabilities(0.4, 0.2), {"00": 0.3, "10": 0.2, "01": 0.1, "11": 0.4}
        )

    def test_duplicate_missing_and_changed_counts_rejected(self):
        for mutation in ("duplicate", "missing", "counts", "binding"):
            report = copy.deepcopy(self.report)
            if mutation == "duplicate":
                report["records"][-1] = report["records"][0]
            elif mutation == "missing":
                report["records"].pop()
            elif mutation == "counts":
                report["records"][0]["counts"] = {"01": 16384}
            else:
                report["records"][0]["options"]["readout"]["p10"] = 0.4
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate(report)
