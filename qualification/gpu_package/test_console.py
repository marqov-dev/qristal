import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("package_recovery", HERE / "console.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
EVIDENCE = HERE.parent / "evidence/2026-09-11-gpu-package"


class Console(unittest.TestCase):
    def test_saved_recovery_preserves_payload_and_records(self):
        report, complete, truncated = recovery.recover(
            (EVIDENCE / "console-observed.txt").read_text()
        )
        self.assertEqual(report, json.loads((EVIDENCE / "result.json").read_text()))
        self.assertEqual(complete, (EVIDENCE / "console-chunks.txt").read_text())
        self.assertEqual(truncated, [{"index": 37, "length": 141}])

    def test_missing_full_copy_rejected(self):
        text = (EVIDENCE / "console-chunks.txt").read_text()
        lines = [line for line in text.splitlines() if line.split()[2] != "37"]
        with self.assertRaises(ValueError):
            recovery.recover("\n".join(lines))

    def test_conflicting_complete_or_partial_copy_rejected(self):
        text = (EVIDENCE / "console-chunks.txt").read_text()
        fields = text.splitlines()[0].split()
        part = fields[4]
        changed = ("A" if part[0] != "A" else "B") + part[1:]
        for value in (changed, changed[:120]):
            extra = " ".join(fields[:4] + [value])
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                recovery.recover(text + "\n" + extra)

    def test_truncated_record_cannot_change_stream_identity(self):
        text = (EVIDENCE / "console-chunks.txt").read_text()
        fields = text.splitlines()[0].split()
        fields[1] = "0" * 64
        fields[4] = fields[4][:120]
        with self.assertRaises(ValueError):
            recovery.recover(text + "\n" + " ".join(fields))


if __name__ == "__main__":
    unittest.main()
