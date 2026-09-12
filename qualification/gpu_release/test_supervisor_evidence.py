import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_supervisor import check

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-supervisor-recovery"


class NativeSupervisorEvidence(unittest.TestCase):
    def mutate(self, filename, change):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "evidence"
        shutil.copytree(EVIDENCE, root)
        path = root / filename
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))
        # Rehash so semantic checks, not only byte integrity, must reject it.
        manifest = json.loads((root / "manifest.json").read_text())
        manifest["files"][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / "manifest.json").write_text(json.dumps(manifest))
        return root

    def test_native_record_replays_without_aws(self):
        self.assertTrue(check(EVIDENCE)["verified"])

    def test_restart_cannot_extend_original_deadline(self):
        root = self.mutate("supervisor.json", lambda data: data.update(
            observe_until=data["observe_until"] + 60))
        with self.assertRaisesRegex(ValueError, "deadline_changed"):
            check(root)

    def test_different_disk_cannot_pass_cleanup(self):
        root = self.mutate("cleanup.json", lambda data: data.update(
            volume_ids=["vol-00000000000000000"]))
        with self.assertRaisesRegex(ValueError, "cleanup_identity"):
            check(root)

    def test_incomplete_cleanup_cannot_pass(self):
        root = self.mutate("resources.json", lambda data: data.update(cleanup_verified=False))
        with self.assertRaisesRegex(ValueError, "cleanup_incomplete"):
            check(root)

    def test_modified_recovered_payload_rejected(self):
        root = self.mutate("recovered.json", lambda data: data["result"].update(
            gpu_probe_returncode=1))
        with self.assertRaisesRegex(ValueError, "result_mismatch"):
            check(root)


if __name__ == "__main__":
    unittest.main()
