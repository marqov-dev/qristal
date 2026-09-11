import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("release_candidate", HERE / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class Release(unittest.TestCase):
    def test_context_is_exact_and_retains_license_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = root / "context"
            record = root / "record.json"
            release.stage(context, record, "a" * 40)
            data = json.loads(record.read_text())
            self.assertEqual(
                set(data["context_files"]), {p.name for p in context.iterdir()}
            )
            for name, digest in data["context_files"].items():
                self.assertEqual(release.sha((context / name).read_bytes()), digest)
            self.assertEqual(
                json.loads((context / "payload.json").read_text()), data["payload"]
            )
            dockerfile = (context / "Dockerfile").read_text()
            self.assertIn("NOTICE.release.md", dockerfile)
            self.assertNotIn('org.opencontainers.image.licenses="Apache', dockerfile)
            self.assertEqual(dockerfile.splitlines()[0], "FROM " + release.BASE)

    def test_mutable_revision_fails_before_creating_context(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "context"
            with self.assertRaises(ValueError):
                release.stage(output, Path(directory) / "record.json", "main")
            self.assertFalse(output.exists())

    def test_receipt_binds_registry_digest_and_does_not_promote(self):
        result = release.receipt(
            {"source_revision": "a" * 40}, "sha256:" + "b" * 64, "123", "1"
        )
        self.assertEqual(result["image"], release.IMAGE + "@sha256:" + "b" * 64)
        self.assertFalse(result["hosted_available"])
        self.assertEqual(result["status"], "published_candidate_not_gpu_qualified")

    def test_missing_or_mutable_registry_identity_rejects(self):
        for digest in ("latest", "sha256:short", ""):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                release.receipt({"source_revision": "a" * 40}, digest, "123", "1")


if __name__ == "__main__":
    unittest.main()
