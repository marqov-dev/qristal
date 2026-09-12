import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from verify import verify


class PacketTests(unittest.TestCase):
    def check_archive(self,mutate):
        contents={"index.html":b"<html>demo</html>","evidence/example.json":b"{}"}
        manifest=dict(kind="conference-evidence-subset",revision="a"*40,
                      native_execution_performed_by_export=False,
                      files={"example.json":hashlib.sha256(b"{}").hexdigest()},
                      html_sha256=hashlib.sha256(contents["index.html"]).hexdigest())
        mutate(contents,manifest)
        contents["manifest.json"]=json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"packet.zip"
            with zipfile.ZipFile(path,"w") as archive:
                for name,raw in contents.items(): archive.writestr(name,raw)
            return verify(path)

    def test_valid_subset(self):
        self.assertEqual(self.check_archive(lambda c,m:None)["publisher_authenticity"],"not_verified")

    def test_changed_evidence(self):
        with self.assertRaisesRegex(ValueError,"content_hash"):
            self.check_archive(lambda c,m:c.update({"evidence/example.json":b'{"changed":true}'}))

    def test_extra_file(self):
        with self.assertRaisesRegex(ValueError,"archive_inventory"):
            self.check_archive(lambda c,m:c.update({"unexpected.txt":b"x"}))

    def test_native_claim(self):
        with self.assertRaisesRegex(ValueError,"manifest_scope"):
            self.check_archive(lambda c,m:m.update(native_execution_performed_by_export=True))

    def test_path_escape(self):
        with self.assertRaisesRegex(ValueError,"file_inventory"):
            self.check_archive(lambda c,m:m.update(files={"../outside":"a"*64}))
