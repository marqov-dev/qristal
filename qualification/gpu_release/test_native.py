"""Replay the real retained release; reject changed identity and cleanup evidence."""

import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_native import main, verify, verify_retained

ROOT = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-published"


class NativeReleaseTests(unittest.TestCase):
    def test_complete_native_record(self):
        with contextlib.redirect_stdout(io.StringIO()):
            main(ROOT)

    def test_identity_and_transport_mutations(self):
        original = json.loads((ROOT / "result.json").read_text())
        transfer = json.loads((ROOT / "transfer.json").read_text())
        for key in (
            "registry_image",
            "platform_manifest",
            "configuration",
            "archive_sha256",
            "source_revision",
        ):
            report = copy.deepcopy(original)
            report["build"]["release_binding"][key] = "changed"
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify(report, ROOT / "release", transfer)
        report = copy.deepcopy(original)
        report["build"]["image_id"] = "sha256:" + "0" * 64
        with self.assertRaises(ValueError):
            verify(report, ROOT / "release", transfer)
        transfer["source_revision"] = "changed"
        with self.assertRaises(ValueError):
            verify(original, ROOT / "release", transfer)

    def test_retained_bytes_and_staged_source_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence"
            shutil.copytree(ROOT, target)
            path = target / "release/sbom.json.gz"
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.assertRaises((ValueError, OSError, EOFError)):
                verify_retained(target)
            path.write_bytes(original)
            sources = json.loads((target / "source-hashes.json").read_text())
            sources["qualification/gpu_release/import_image.py"] = "0" * 64
            (target / "source-hashes.json").write_text(json.dumps(sources))
            with self.assertRaisesRegex(ValueError, "staged_source_binding"):
                verify_retained(target)

    def test_cleanup_and_console_mutations(self):
        for name, key in (
            ("cleanup.json", "instance_absent"),
            ("cleanup.json", "volumes_absent"),
            ("cleanup.json", "security_group_deleted"),
            ("transfer-cleanup.json", "bucket_absent"),
        ):
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "evidence"
                shutil.copytree(ROOT, target)
                record = json.loads((target / name).read_text())
                record[key] = False
                (target / name).write_text(json.dumps(record))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    main(target)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence"
            shutil.copytree(ROOT, target)
            (target / "console-chunks.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError, "console_binding"):
                main(target)

    def test_volume_window_must_cover_launch_and_be_empty(self):
        for field, value in (
            ("matching_volumes", [{"id": "unresolved-volume"}]),
            ("from_inclusive", "2026-09-11T10:22:00+00:00"),
        ):
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "evidence"
                shutil.copytree(ROOT, target)
                record = json.loads((target / "cleanup.json").read_text())
                record["volume_verification"][field] = value
                (target / "cleanup.json").write_text(json.dumps(record))
                with (
                    self.subTest(field=field),
                    self.assertRaisesRegex(ValueError, "launch_window_cleanup"),
                ):
                    main(target)
