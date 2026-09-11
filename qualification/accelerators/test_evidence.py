"""Negative tests use synthetic evidence, never counted as a native GPU pass."""

import copy
import json
from pathlib import Path
from normalize_console import normalize
import hashlib
import unittest

from check_evidence import verify_gpu
from fixtures import SHOTS, TOLERANCE, cases, qasm


def synthetic_report():
    results = []
    for target, library in [
        ("nvidia", "libcustatevec.so"),
        ("tensornet", "libcutensornet.so"),
    ]:
        results.append(
            dict(
                target=target,
                gpu_count=1,
                shots=SHOTS,
                tolerance=TOLERANCE,
                cudaq_version="synthetic",
                libraries=["/synthetic/" + library],
                records=[
                    dict(
                        case=c["name"],
                        expected=c["expected"],
                        counts={
                            key: int(p * SHOTS) for key, p in c["expected"].items()
                        },
                        program_sha256=hashlib.sha256(qasm(c).encode()).hexdigest(),
                    )
                    for c in cases()
                ],
            )
        )
    return dict(
        hardware="synthetic",
        owned_containers_absent=True,
        image="nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a",
        results=results,
    )


class EvidenceTests(unittest.TestCase):
    def test_retained_gpu_results_and_transport_copies(self):
        directory = (
            Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-feasibility"
        )
        report = json.loads((directory / "result.json").read_text())
        verify_gpu(report)
        self.assertEqual(
            normalize((directory / "console-payloads.txt").read_text()), report
        )

    def test_console_copy_disagreement_rejects(self):
        with self.assertRaisesRegex(ValueError, "console_copies_disagree"):
            normalize('{"count": 1}\n{"count": 2}\n')
        with self.assertRaisesRegex(ValueError, "two_console_copies_required"):
            normalize('{"count": 1}\n')

    def test_fixed_synthetic_shape(self):
        verify_gpu(synthetic_report())

    def test_wrong_target_missing_gpu_or_library_rejects(self):
        for field, value in [
            ("target", "qpp-cpu"),
            ("gpu_count", 0),
            ("libraries", []),
        ]:
            report = synthetic_report()
            report["results"][0][field] = value
            with self.assertRaises(ValueError):
                verify_gpu(report)

    def test_missing_or_duplicate_target_rejects(self):
        for duplicate in (False, True):
            report = synthetic_report()
            report["results"] = [report["results"][0]]
            if duplicate:
                report["results"].append(copy.deepcopy(report["results"][0]))
            with self.assertRaises(ValueError):
                verify_gpu(report)

    def test_wrong_image_and_cleanup_rejects(self):
        for field, value in [
            ("image", "unbound:latest"),
            ("owned_containers_absent", False),
        ]:
            report = synthetic_report()
            report[field] = value
            with self.assertRaises(ValueError):
                verify_gpu(report)

    def test_changed_input_missing_case_and_bad_counts_rejects(self):
        for kind in ("hash", "missing", "counts"):
            report = synthetic_report()
            records = report["results"][0]["records"]
            if kind == "hash":
                records[0]["program_sha256"] = "0" * 64
            elif kind == "missing":
                records.pop()
            else:
                records[0]["counts"] = {"001": SHOTS}
            with self.assertRaises(ValueError):
                verify_gpu(report)


if __name__ == "__main__":
    unittest.main()
