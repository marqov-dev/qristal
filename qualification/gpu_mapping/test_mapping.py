import copy
from dataclasses import replace
import hashlib
import json
import unittest
from pathlib import Path

from mapping import validate
from replay import cases, context, records, replay


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.expected = context("nvidia", cases()[0])
        self.candidate = copy.deepcopy(
            next(
                r["candidate"]
                for r in records()
                if r["case"] == "x-first" and r["candidate"]["target"] == "nvidia"
            )
        )

    def run_candidate(self, candidate=None, raw=None, expected=None):
        return validate(
            json.dumps(self.candidate if candidate is None else candidate).encode(),
            self.raw if raw is None else raw,
            self.expected if expected is None else expected,
        )

    def test_all_native_cases_and_synthetic_engine_parity(self):
        report = replay()
        self.assertEqual(len(report["cases"]), 12)
        self.assertTrue(all(r["synthetic_engine_parity"] for r in report["cases"]))

    def test_retained_replay_and_source_manifest(self):
        base = Path(__file__).resolve().parents[1]
        directory = base / "evidence/2026-09-11-gpu-mapping"
        self.assertEqual(json.loads((directory / "replay.json").read_text()), replay())
        manifest = json.loads((directory / "manifest.json").read_text())
        for name, digest in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((base / name).read_bytes()).hexdigest(), digest, name
            )

    def test_display_map_and_no_authority_receipt(self):
        result = self.run_candidate()
        self.assertEqual(result["positions"], ["q[0]", "q[1]", "q[2]"])
        self.assertEqual(result["counts"], {"100": 16384})
        self.assertEqual(
            result["shots"],
            dict(requested=16384, successful=16384, discarded=0, unknown=0),
        )
        self.assertFalse(
            set(result)
            & {"receipt", "accepted", "provider_handle", "state", "operation_id"}
        )

    def test_changed_candidate_bindings(self):
        replacements = dict(
            input_sha256="0" * 64,
            adapter_sha256="0" * 64,
            runtime_image="floating:latest",
            cudaq_version="other",
            target="tensornet",
            qubits=2,
            shots=17,
            seed=7,
        )
        for key, value in replacements.items():
            candidate = copy.deepcopy(self.candidate)
            candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_candidate(candidate)

    def test_independent_context_mismatch(self):
        for changes in (
            {"target": "tensornet"},
            {"input_sha256": "0" * 64},
            {"adapter_sha256": "0" * 64},
            {"runtime_image": "other"},
            {"shots": 17},
            {"cudaq_version": "other"},
            {"libraries": ()},
            {"positions": tuple(reversed(self.expected.positions))},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_candidate(expected=replace(self.expected, **changes))

    def test_changed_input_even_if_candidate_echoes_hash(self):
        raw = self.raw + b" "
        self.candidate["input_sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):
            self.run_candidate(raw=raw)

    def test_matching_claims_do_not_override_admitted_target(self):
        artifact = json.loads(self.raw)
        artifact["target"] = "tensornet"
        raw = json.dumps(artifact, sort_keys=True).encode()
        expected = replace(self.expected, input_sha256=hashlib.sha256(raw).hexdigest())
        self.candidate["input_sha256"] = expected.input_sha256
        self.candidate["target"] = "tensornet"
        with self.assertRaises(ValueError):
            self.run_candidate(raw=raw, expected=expected)

    def test_missing_extra_and_cpu_fallback(self):
        for mode in ("missing", "extra", "cpu", "gpu_bool", "order", "library"):
            candidate = copy.deepcopy(self.candidate)
            if mode == "missing":
                candidate.pop("counts")
            elif mode == "extra":
                candidate["accepted"] = True
            elif mode == "cpu":
                candidate["target"] = "qpp-cpu"
            elif mode == "gpu_bool":
                candidate["gpu_count"] = True
            elif mode == "order":
                candidate["bit_order"] = "little-endian"
            else:
                candidate["libraries"] = []
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.run_candidate(candidate)

    def test_invalid_counts(self):
        for counts in (
            {},
            {"100": True},
            {"100": 16384.0},
            {"100": 16383},
            {"100": 16385},
            {"100": 16384, "000": 0},
            {"10": 16384},
            {"xxx": 16384},
            [],
        ):
            candidate = copy.deepcopy(self.candidate)
            candidate["counts"] = counts
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                self.run_candidate(candidate)

    def test_duplicate_trailing_nonfinite_and_size(self):
        raw = json.dumps(self.candidate).encode()
        for bad in (
            b"",
            raw + b"{}",
            raw[:-1] + b',"shots":16384}',
            raw.replace(b"16384", b"NaN"),
            b"x" * 131073,
            b"\xff",
        ):
            with self.assertRaises(ValueError):
                validate(bad, self.raw, self.expected)

    def test_input_gate_rejections_even_with_bound_hash(self):
        for gate in (["rx", 0, 0.1], ["cx", 0, 0], ["x", True], ["x", 3]):
            artifact = json.loads(self.raw)
            artifact["gates"] = [gate]
            raw = json.dumps(artifact).encode()
            digest = hashlib.sha256(raw).hexdigest()
            candidate = copy.deepcopy(self.candidate)
            candidate["input_sha256"] = digest
            with self.assertRaises(ValueError):
                self.run_candidate(
                    candidate, raw, replace(self.expected, input_sha256=digest)
                )

    def test_plausible_wrong_counts_are_not_execution_proof(self):
        # Mapping integrity cannot establish the quantum circuit actually executed.
        self.candidate["counts"] = {"001": 16384}
        self.assertEqual(self.run_candidate()["counts"], {"001": 16384})


if __name__ == "__main__":
    unittest.main()
