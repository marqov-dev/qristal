import copy
import json
from pathlib import Path
import unittest
from check_evidence import verify
from console import decode

DIRECTORY = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-adapter"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((DIRECTORY / "result.json").read_text())

    def test_saved_native_matrix_and_chunks(self):
        verify(self.report)
        self.assertEqual(
            decode((DIRECTORY / "console-chunks.txt").read_text()), self.report
        )

    def test_changed_candidate_input_and_output_rejects(self):
        for kind in ("digest", "counts", "target", "adapter", "case"):
            report = copy.deepcopy(self.report)
            record = report["records"][0]
            if kind == "digest":
                record["candidate"]["input_sha256"] = "0" * 64
            elif kind == "counts":
                record["candidate"]["counts"] = {"001": 16384}
            elif kind == "target":
                record["candidate"]["target"] = "qpp-cpu"
            elif kind == "adapter":
                record["candidate"]["adapter_sha256"] = "0" * 64
            else:
                report["records"].pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify(report)

    def test_completion_without_stop_or_gpu_release_rejects(self):
        for kind in ("stopped", "context", "released", "missing_fault", "recovery"):
            report = copy.deepcopy(self.report)
            if kind == "stopped":
                report["faults"][0]["stopped_observed"] = False
            elif kind == "context":
                report["faults"][0]["owned_gpu_context_observed"] = False
            elif kind == "released":
                report["gpu_processes_absent"] = False
            elif kind == "missing_fault":
                report["faults"].pop()
            else:
                report["recovery"]["candidate"]["counts"] = {}
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify(report)


if __name__ == "__main__":
    unittest.main()
