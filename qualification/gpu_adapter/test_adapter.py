import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from adapter import execute, parse, read_artifact


def artifact(**updates):
    data = dict(
        schema="qristal.cudaq-circuit/v1",
        target="nvidia",
        qubits=3,
        shots=17,
        seed=42,
        gates=[["x", 0]],
    )
    data.update(updates)
    raw = json.dumps(data).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def fake_runtime(counts=None, target="nvidia", gpus=1):
    kernel = SimpleNamespace(
        qalloc=lambda n: list(range(n)),
        x=lambda *a: None,
        h=lambda *a: None,
        cx=lambda *a: None,
        mz=lambda *a: None,
    )
    return SimpleNamespace(
        num_available_gpus=lambda: gpus,
        set_target=lambda *a, **k: None,
        get_target=lambda: SimpleNamespace(name=target),
        make_kernel=lambda: kernel,
        set_random_seed=lambda seed: None,
        sample=lambda *a, **k: {"100": 17} if counts is None else counts,
        __version__="synthetic",
    )


class AdapterTests(unittest.TestCase):
    def test_artifact_binding(self):
        raw, digest = artifact()
        self.assertEqual(parse(raw, digest)["gates"], [["x", 0]])
        for changed in (raw + b" ", b"", b" " * 16385):
            with self.assertRaises(ValueError):
                parse(changed, digest)
        with self.assertRaises(ValueError):
            parse(raw, "0" * 64)

    def test_closed_shape_and_duplicate_members(self):
        raw, _ = artifact()
        for bad in (raw[:-1] + b',"target":"nvidia"}', b"[]", b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                parse(bad, hashlib.sha256(bad).hexdigest())
        data = json.loads(raw)
        data["code"] = "print(1)"
        bad = json.dumps(data).encode()
        with self.assertRaises(ValueError):
            parse(bad, hashlib.sha256(bad).hexdigest())

    def test_bounds_and_unsupported_targets(self):
        for key, values in {
            "qubits": [0, 13, True, 2.0],
            "shots": [0, 16385, True],
            "seed": [-1, 2**31, False],
            "target": ["qpp-cpu", "cudaq:qb_mps", "automatic"],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    parse(*artifact(**{key: value}))

    def test_gate_rejections(self):
        for gates in (
            [],
            [["rx", 0, 0.3]],
            [["x", True]],
            [["x", 3]],
            [["cx", 0, 0]],
            [["measure", 0]],
            [["h", 0, 1]],
            [[[]]],
            [["x", 0]] * 257,
        ):
            with self.subTest(gates=gates[:2]), self.assertRaises(ValueError):
                parse(*artifact(gates=gates))

    def test_regular_file_only_and_size_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "input"
            p.write_bytes(b"x" * 20000)
            self.assertEqual(len(read_artifact(p)), 16385)
            link = root / "link"
            link.symlink_to(p)
            with self.assertRaises(OSError):
                read_artifact(link)
            with self.assertRaises((OSError, ValueError)):
                read_artifact(root)

    def test_reject_before_runtime_import(self):
        with patch.dict(sys.modules, {"cudaq": None}), self.assertRaises(ValueError):
            execute(*artifact(gates=[["unknown", 0]]))

    def test_missing_gpu_and_wrong_target(self):
        for runtime in (fake_runtime(gpus=0), fake_runtime(target="qpp-cpu")):
            with (
                patch.dict(sys.modules, {"cudaq": runtime}),
                self.assertRaises(RuntimeError),
            ):
                execute(*artifact())

    def test_missing_or_invalid_output(self):
        for counts in (
            {},
            {"100": 16},
            {"1": 17},
            {"100": True},
            {"100": 17.0},
            {"xxx": 17},
        ):
            with (
                patch.dict(sys.modules, {"cudaq": fake_runtime(counts)}),
                self.assertRaises(RuntimeError),
            ):
                execute(*artifact())

    def test_candidate_binding_and_library_evidence(self):
        raw, digest = artifact()
        with (
            patch.dict(sys.modules, {"cudaq": fake_runtime()}),
            patch(
                "adapter.libraries",
                return_value=["/lib/libnvqir-cusvsim-fp64.so", "/lib/libcustatevec.so"],
            ),
        ):
            result = execute(raw, digest)
        self.assertEqual(result["input_sha256"], digest)
        self.assertEqual(result["counts"], {"100": 17})
        self.assertEqual(result["schema"], "qristal.cudaq-candidate/v1")
        self.assertNotIn("accepted", result)
        with (
            patch.dict(sys.modules, {"cudaq": fake_runtime()}),
            patch("adapter.libraries", return_value=[]),
            self.assertRaises(RuntimeError),
        ):
            execute(raw, digest)


if __name__ == "__main__":
    unittest.main()
