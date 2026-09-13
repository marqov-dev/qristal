import json
from pathlib import Path
import tempfile
import unittest
import verify_materials as materials

class MaterialTests(unittest.TestCase):
    def fixture(self, root):
        (root/'input').mkdir(); (root/'input/data').write_bytes(b'data')
        (root/'input/link').symlink_to('data')
        (root/'material-manifest.json').write_text(json.dumps({'schema':'qb.core-material-manifest/v1','entries':materials.inventory(root)}))
    def test_roundtrip_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.assertTrue(materials.verify(root)['verified'])
            (root/'input/data').write_bytes(b'changed')
            with self.assertRaises(ValueError):materials.verify(root)
    def test_extra_missing_and_mode_changes(self):
        for change in ('extra','missing','mode'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.fixture(root)
                if change=='extra':(root/'unexpected').write_bytes(b'x')
                elif change=='missing':(root/'input/link').unlink()
                else:(root/'input/data').chmod(0o600)
                with self.assertRaises(ValueError):materials.verify(root)
    def test_external_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'outside').symlink_to('/etc/hosts')
            with self.assertRaisesRegex(ValueError,'escaping'):materials.inventory(root)

class SourceMutationTests(unittest.TestCase):
    def test_only_generated_core_header_is_allowed(self):
        import shutil
        from stage_work import audit_core
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'original';source.mkdir()
            (source/'include/qristal/core').mkdir(parents=True)
            (source/'source.cpp').write_text('source')
            derived=root/'derived';shutil.copytree(source,derived)
            with self.assertRaises(ValueError):audit_core(source,derived)
            (derived/'include/qristal/core/cmake_variables.hpp').write_text('generated')
            self.assertTrue(audit_core(source,derived)['only_generated_header_changed'])
            (derived/'material-manifest.json').write_text('unexpected')
            with self.assertRaises(ValueError):audit_core(source,derived)
            (derived/'material-manifest.json').unlink()
            (derived/'source.cpp').write_text('modified')
            with self.assertRaises(ValueError):audit_core(source,derived)
