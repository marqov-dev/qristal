import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('attribution',Path(__file__).with_name('attribution.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AttributionTests(unittest.TestCase):
    def test_bound_copy_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();(source/'notice').write_bytes(b'notice')
            expected={'bytes':6,'sha256':a.hashlib.sha256(b'notice').hexdigest()}
            a.pin(source,'notice',root/'copy',expected)
            self.assertEqual((root/'copy').read_bytes(),b'notice')
            (source/'notice').write_bytes(b'edited')
            with self.assertRaises(ValueError):a.pin(source,'notice',root/'bad',expected)

    def test_traversal_symlink_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'link').symlink_to('/tmp');entries={};expected={'bytes':1,'sha256':a.hashlib.sha256(b'x').hexdigest()}
            for name in ('../escape','/absolute','link/notice'):
                with self.assertRaises(ValueError):a.write_notice(root,name,b'x',expected,'test',{},entries)
            a.write_notice(root,'safe',b'x',expected,'test',{},entries)
            with self.assertRaises(ValueError):a.write_notice(root,'safe',b'x',expected,'test',{},entries)
            self.assertEqual((root/'safe').read_bytes(),b'x')

    def test_pinned_inventory_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'inventory.json').write_text('{}')
            with self.assertRaises(ValueError):a.pinned_document(root,'inventory.json',root/'copy','0'*64)

    def test_exact_file_inventory_rejects_extra_missing_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'inventory.json').write_text('{}');(root/'notice').write_text('notice')
            entries={'notice':{'type':'file'}}
            a.exact_files(root,entries,'inventory.json')
            (root/'extra').write_text('extra')
            with self.assertRaises(ValueError):a.exact_files(root,entries,'inventory.json')
            (root/'extra').unlink();(root/'notice').unlink()
            with self.assertRaises(ValueError):a.exact_files(root,entries,'inventory.json')
            (root/'notice').symlink_to('/tmp')
            with self.assertRaises(ValueError):a.exact_files(root,entries,'inventory.json')

    def test_never_overwrite_existing_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sentinel=root/'sentinel';sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):a.build(root,root,root,root)
            self.assertEqual(sentinel.read_text(),'keep')

if __name__=='__main__':unittest.main()
