import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_evidence import check

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/2026-09-12-readout-drift"


class Evidence(unittest.TestCase):
    def mutate(self, name, change):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "proof"
        shutil.copytree(EVIDENCE, root)
        data = json.loads((root / name).read_text())
        change(data)
        (root / name).write_text(json.dumps(data))
        manifest = json.loads((root / "manifest.json").read_text())
        manifest["files"][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        (root / "manifest.json").write_text(json.dumps(manifest))
        return root

    def test_native_calibration_and_held_out_replay(self):
        summary = check(EVIDENCE)
        self.assertEqual(len(summary["outcomes"]), 60)
        self.assertTrue(all(row["mae"]["fresh"] <= .5*row["mae"]["raw"]
                            for row in summary["settings"]))

    def test_changed_analysis_rejected_even_with_updated_file_hash(self):
        root = self.mutate("analysis.json", lambda data: data["outcomes"][0].update(fresh=0))
        with self.assertRaisesRegex(ValueError, "analysis_changed"):
            check(root)

    def test_different_container_cleanup_rejected(self):
        root = self.mutate("demo-cleanup.json", lambda data: data.update(name="another-container"))
        with self.assertRaisesRegex(ValueError, "cleanup"):
            check(root)

    def test_saved_counts_must_match_native_stdout(self):
        root = self.mutate("result.json", lambda data: data["records"][0].update(counts={"00": 16384}))
        with self.assertRaisesRegex(ValueError, "native_output"):
            check(root)


if __name__ == "__main__":
    unittest.main()
