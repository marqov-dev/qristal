import json
from pathlib import Path
import shutil
import tempfile
import unittest
from check_evidence import EVIDENCE, check


class EvidenceTests(unittest.TestCase):
    def test_replay(self):
        self.assertFalse(check()["native_execution"])

    def test_changed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            for source in EVIDENCE.iterdir():
                if source.suffix == ".json":
                    shutil.copyfile(source,path/source.name)
            counts=json.loads((path/"counts.json").read_text())
            counts[0]["held_out"]={"00":16384}
            (path/"counts.json").write_text(json.dumps(counts))
            with self.assertRaisesRegex(ValueError,"file_hash"):
                check(path)

    def test_native_claim_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            manifest=json.loads((EVIDENCE/"manifest.json").read_text())
            manifest["native_execution"]=True
            (path/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"execution_kind"):
                check(path)
