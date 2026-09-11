import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "package_qualification", HERE / "qualify.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class Commands(unittest.TestCase):
    def test_only_input_mount_and_baked_code(self):
        command = package.command(
            "test",
            "sha256:" + "a" * 64,
            Path("/tmp/inputs"),
            ["/probe/adapter.py", "/probe/inputs/circuit.json", "--sha256", "b" * 64],
        )
        self.assertEqual(command.count("--mount"), 1)
        self.assertEqual(
            command[command.index("--mount") + 1],
            "type=bind,source=/tmp/inputs,target=/inputs,readonly",
        )
        self.assertIn("/opt/marqov-qb/adapter.py", command)
        self.assertIn("/inputs/circuit.json", command)
        self.assertNotIn("/probe/adapter.py", command)
        self.assertIn("none", command)
        self.assertIn("--read-only", command)

    def test_mutable_image_rejected(self):
        for image in ("latest", "test:tag", "sha256:short"):
            with self.subTest(image=image), self.assertRaises(ValueError):
                package.command("test", image, Path("/tmp/inputs"), [])

    def test_negative_gpu_visibility(self):
        command = package.command(
            "test", "sha256:" + "a" * 64, Path("/tmp/inputs"), [], False
        )
        self.assertNotIn("--gpus", command)
        self.assertIn("NVIDIA_VISIBLE_DEVICES=void", command)


if __name__ == "__main__":
    unittest.main()
