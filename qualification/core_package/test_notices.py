import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec=importlib.util.spec_from_file_location('notices',Path(__file__).with_name('notices.py'))
notices=importlib.util.module_from_spec(spec);spec.loader.exec_module(notices)


class NoticeTests(unittest.TestCase):
    def wheel(self,path,license=True,extra=None):
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('demo.dist-info/METADATA','Metadata-Version: 2.1\nName: demo\nVersion: 1\nLicense: Apache-2.0\nLicense-File: terms.txt\n')
            if license:archive.writestr('demo.dist-info/terms.txt','example license text')
            if extra:archive.writestr(*extra)

    def test_declared_custom_name_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'demo.whl';self.wheel(path)
            result=notices.scan_wheel(path)
            self.assertEqual(result['metadata']['fields']['Name'],['demo'])
            self.assertEqual(result['notice_files'][0]['path'],'demo.dist-info/terms.txt')
            self.assertEqual(result['declared_license_files_not_found'],[])

    def test_missing_notice_is_coverage_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'demo.whl';self.wheel(path,False)
            result=notices.scan_wheel(path)
            self.assertEqual(result['notice_files'],[])
            self.assertEqual(result['declared_license_files_not_found'],['terms.txt'])

    def test_traversal_and_oversized_notice_rejected(self):
        for name in ('../LICENSE','demo.dist-info/LICENSE'):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'demo.whl';self.wheel(path,extra=(name,'x'*1000))
                with patch.object(notices,'MAX_MEMBER',500),self.assertRaises(ValueError):notices.scan_wheel(path)

    def test_native_notice_inventory_no_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'work.tar';raw=b'example copyright'
            with tarfile.open(path,'w') as archive:
                member=tarfile.TarInfo('install-core/LICENSE');member.size=len(raw)
                archive.addfile(member,io.BytesIO(raw))
            result=notices.scan_work(path)
            self.assertEqual(result['notice_files'][0]['sha256'],notices.sha(raw))
            self.assertEqual(result['install_roots_without_filename_matched_notices'],['install-xacc'])
            self.assertEqual(list(Path(tmp).iterdir()),[path])

    def test_scan_binds_all_inputs_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);wheels=root/'python/wheels';wheels.mkdir(parents=True)
            for i in range(51):self.wheel(wheels/(str(i)+'.whl'))
            with tarfile.open(root/'work.tar','w'):pass
            paths=list(wheels.iterdir())+[root/'work.tar']
            inventory={p.relative_to(root).as_posix():{'type':'file','bytes':p.stat().st_size,'sha256':notices.file_sha(p)} for p in paths}
            (root/'staging.json').write_text(json.dumps({'schema':'qb.core-staged-inputs/v1','staged':True,'inventory':inventory}))
            result=notices.scan(root)
            self.assertEqual(result['wheel_count'],51);self.assertFalse(result['coverage_complete'])
            self.assertEqual(len(result['input_bindings']),52)
            paths[0].write_bytes(b'changed')
            with self.assertRaises(ValueError):notices.scan(root)

if __name__=='__main__':unittest.main()
