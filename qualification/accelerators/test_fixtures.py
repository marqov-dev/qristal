import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fixtures import SHOTS, cases, check, qasm
from gpu_probe import main


class FixtureTests(unittest.TestCase):
    def test_fixed_matrix_names_and_programs(self):
        fixtures = cases()
        self.assertEqual(len({c["name"] for c in fixtures}), 6)
        for case in fixtures:
            self.assertTrue(qasm(case).startswith("OPENQASM 2.0;"))
            self.assertEqual(sum(case["expected"].values()), 1)
            self.assertTrue(all(len(k) == case["qubits"] for k in case["expected"]))

    def test_exact_endpoints(self):
        case = cases()[0]
        check({"100": SHOTS}, case)
        for bad in (
            {"001": SHOTS},
            {"100": SHOTS - 1},
            {"100": True},
            {"100": float(SHOTS)},
            {"100": SHOTS, "000": 0},
        ):
            with self.assertRaises(ValueError):
                check(bad, case)

    def test_coherence_and_correlation_failures_reject(self):
        with self.assertRaises(ValueError):
            check({"100": SHOTS // 2, "000": SHOTS // 2}, cases()[2])
        with self.assertRaises(ValueError):
            check({"00": SHOTS}, cases()[3])
        with self.assertRaises(ValueError):
            check({"01": SHOTS // 2, "10": SHOTS // 2}, cases()[3])

    def test_no_gpu_rejects_before_selection(self):
        fake = SimpleNamespace(num_available_gpus=lambda: 0)
        with (
            patch.dict(sys.modules, {"cudaq": fake}),
            self.assertRaisesRegex(RuntimeError, "gpu_required"),
        ):
            main("nvidia")

    def test_target_mismatch_rejects_without_fallback(self):
        calls = []
        fake = SimpleNamespace(
            num_available_gpus=lambda: 1,
            set_target=lambda *a, **k: calls.append((a, k)),
            get_target=lambda: SimpleNamespace(name="qpp-cpu"),
        )
        with (
            patch.dict(sys.modules, {"cudaq": fake}),
            self.assertRaisesRegex(RuntimeError, "target_mismatch"),
        ):
            main("nvidia")
        self.assertEqual(calls, [(("nvidia",), {"option": "fp64"})])

    def test_unsupported_target_rejects(self):
        for target in ("cudaq:qb_mps", "cudaq:dm", "qpp-cpu", "automatic"):
            with self.assertRaisesRegex(ValueError, "target_rejected"):
                main(target)

    def test_sample_result_key_iteration_uses_items(self):
        # Regression for CUDA-Q SampleResult: iteration yields keys, not pairs.
        class Sample:
            def __init__(self, counts):
                self.counts = counts

            def __iter__(self):
                return iter(self.counts)

            def items(self):
                return self.counts.items()

        samples = iter(
            Sample({k: int(v * SHOTS) for k, v in c["expected"].items()})
            for c in cases()
        )
        kernel = SimpleNamespace(
            qalloc=lambda n: list(range(n)),
            x=lambda *a: None,
            h=lambda *a: None,
            cx=lambda *a: None,
            mz=lambda *a: None,
        )
        fake = SimpleNamespace(
            num_available_gpus=lambda: 1,
            set_target=lambda *a, **k: None,
            get_target=lambda: SimpleNamespace(name="nvidia"),
            make_kernel=lambda: kernel,
            set_random_seed=lambda seed: None,
            sample=lambda *a, **k: next(samples),
            __version__="synthetic",
        )
        output = io.StringIO()
        with (
            patch.dict(sys.modules, {"cudaq": fake}),
            patch(
                "gpu_probe.Path.read_text",
                return_value="mapped /synthetic/libcustatevec.so",
            ),
            redirect_stdout(output),
        ):
            main("nvidia")
        report = json.loads(output.getvalue().removeprefix("QB_GPU_RESULT "))
        self.assertEqual(len(report["records"]), 6)
        self.assertEqual(report["records"][0]["counts"], {"100": SHOTS})

    def test_recorded_cpu_methods_match_each_analytic_fixture(self):
        directory = (
            Path(__file__).resolve().parents[1] / "evidence/2026-09-11-cpu-methods"
        )
        report = json.loads((directory / "cpu.stdout").read_bytes())
        expected = {c["name"]: c for c in cases()}
        observed = set()
        for result in report["records"]:
            key = (result["requested_method"], result["case"])
            self.assertNotIn(key, observed)
            observed.add(key)
            check(result["counts"], expected[result["case"]])
        self.assertEqual(
            observed,
            {
                (m, c)
                for m in ("qpp", "matrix_product_state", "density_matrix")
                for c in expected
            },
        )


if __name__ == "__main__":
    unittest.main()
