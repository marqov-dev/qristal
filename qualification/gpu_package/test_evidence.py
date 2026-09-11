import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "package_checker", HERE / "check_evidence.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class Evidence(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(
            (HERE.parent / "evidence/2026-09-11-gpu-package/result.json").read_text()
        )

    def test_native_evidence(self):
        checker.verify(self.report)

    def test_identity_and_payload_corruption(self):
        for field in ("image", "payload", "base", "recipe"):
            report = copy.deepcopy(self.report)
            if field == "image":
                report["container_observations"][0]["image"] = "sha256:" + "0" * 64
            if field == "payload":
                report["inventory"]["observed_files"]["adapter.py"] = "0" * 64
            if field == "base":
                report["build"]["base"] = "unreviewed:latest"
            if field == "recipe":
                report["build"]["dockerfile_sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                checker.verify(report)

    def test_source_overlay_or_writeable_mount_rejected(self):
        for mutation in ("extra", "write", "destination", "missing"):
            report = copy.deepcopy(self.report)
            mounts = report["container_observations"][0]["mounts"]
            if mutation == "extra":
                mounts.append({"destination": "/probe", "rw": False})
            if mutation == "write":
                mounts[0]["rw"] = True
            if mutation == "destination":
                mounts[0]["destination"] = "/opt/marqov-qb"
            if mutation == "missing":
                report["container_observations"].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                checker.verify(report)

    def test_failed_negative_or_missing_cleanup_evidence_rejected(self):
        for mutation in ("success", "candidate", "running", "missing", "fault"):
            report = copy.deepcopy(self.report)
            if mutation == "success":
                report["negatives"][0]["exit_code"] = 0
            if mutation == "candidate":
                report["negatives"][0]["candidate_absent"] = False
            if mutation == "running":
                report["negatives"][0]["stopped_observed"] = False
            if mutation == "missing":
                report["negatives"].pop()
            if mutation == "fault":
                report["faults"][0]["stopped_observed"] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                checker.verify(report)


if __name__ == "__main__":
    unittest.main()
