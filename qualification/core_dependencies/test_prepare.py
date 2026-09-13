import copy
import difflib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare


class DependencyPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        for name in ('receipts','deps','qualification-inputs'):
            (self.inputs/name).mkdir(parents=True)
        items = []
        self.original = b'# context\noriginal\n# trailing context\n'
        self.changed = self.original.replace(b'original',b'patched')
        patch_text = ''
        for name in sorted(prepare.NAMES):
            root = self.inputs/'deps'/name
            root.mkdir()
            paths = sorted(prepare.EIGEN_FILES) if name == 'eigen3' else ['CMakeLists.txt']
            entries = []
            for path in paths:
                target = root/path
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(self.original)
                entries.append({'path':path,'mode':'100644','git_blob':'fixture',
                                'sha256':prepare.digest(self.original),'bytes':len(self.original)})
                if name == 'eigen3':
                    patch_text += ''.join(difflib.unified_diff(self.original.decode().splitlines(True),
                        self.changed.decode().splitlines(True),fromfile='a/'+path,tofile='b/'+path))
            receipt = {'source':{'commit':'a'*40,'tree':'fixture','entries':entries}}
            raw = json.dumps(receipt).encode()
            (self.inputs/'receipts'/(name+'.json')).write_bytes(raw)
            items.append({'name':name,'cpm_name':'Eigen3' if name=='eigen3' else name,
                          'commit':'a'*40,'receipt_sha256':prepare.digest(raw)})
        materials = {'CPM_0.36.0.cmake':b'# captured script\n','eigen.patch':patch_text.encode()}
        for name,raw in materials.items():
            (self.inputs/'qualification-inputs'/name).write_bytes(raw)
        self.lock = {'schema':'marqov.core-dependency-lock/v1','core_commit':'b'*40,
                     'dependencies':items,'materials':{n:prepare.digest(r) for n,r in materials.items()}}
        self.tools=self.root/'tools'; self.tools.mkdir()
        (self.tools/'lock.json').write_text(json.dumps(self.lock))
        p = patch.object(prepare,'HERE',self.tools)
        p.start();self.addCleanup(p.stop)

    def test_all_eleven_overrides_and_prepatched_eigen_are_bound(self):
        output=self.root/'out'
        report=prepare.prepare(self.inputs,output)
        self.assertEqual(len(report['dependencies']),11)
        self.assertFalse(report['configured'])
        self.assertFalse(report['actual_dependency_selection_verified'])
        config=(output/'overrides.cmake').read_text()
        self.assertIn('CPM_Eigen3_SOURCE',config)
        self.assertNotIn('CPM_eigen3_SOURCE',config)
        self.assertEqual(config.count('_SOURCE "'),11)
        for name in prepare.EIGEN_FILES:
            self.assertEqual((output/'deps/eigen3'/name).read_bytes(),self.changed)
            self.assertEqual((self.inputs/'deps/eigen3'/name).read_bytes(),self.original)
        eigen=next(d for d in report['dependencies'] if d['name']=='eigen3')
        self.assertEqual({c['path'] for c in eigen['changes']},prepare.EIGEN_FILES)
        for item in report['dependencies']:
            raw=(output/'manifests'/(item['name']+'.json')).read_bytes()
            self.assertEqual(prepare.digest(raw),item['effective_manifest_sha256'])
            prepare.export.verify_tree(output/'deps'/item['name'],json.loads(raw))

    def test_extra_or_modified_source_rejected_before_output(self):
        for change in ('extra','modified'):
            with self.subTest(change=change):
                path=self.inputs/'deps/args'/('extra' if change=='extra' else 'CMakeLists.txt')
                path.write_bytes(b'bad')
                with self.assertRaises(ValueError):prepare.prepare(self.inputs,self.root/'out')
                self.assertFalse((self.root/'out').exists())
                if change=='extra':path.unlink()

    def test_bad_material_rejected_before_output(self):
        (self.inputs/'qualification-inputs/eigen.patch').write_bytes(b'not approved')
        with self.assertRaisesRegex(ValueError,'material binding'):
            prepare.prepare(self.inputs,self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_missing_or_duplicate_package_and_wrong_case_rejected(self):
        for change in ('missing','duplicate','case'):
            lock=copy.deepcopy(self.lock)
            if change=='missing':lock['dependencies'].pop()
            elif change=='duplicate':lock['dependencies'][-1]=lock['dependencies'][0]
            else:next(i for i in lock['dependencies'] if i['name']=='eigen3')['cpm_name']='eigen3'
            with self.assertRaises(ValueError):prepare.validate_lock(lock)

    def test_replaced_parent_symlink_rejected(self):
        (self.inputs/'receipts').rename(self.inputs/'original-receipts')
        (self.inputs/'receipts').symlink_to(self.inputs/'original-receipts',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'input directory'):
            prepare.prepare(self.inputs,self.root/'out')

    def test_receipt_change_rejected(self):
        (self.inputs/'receipts/args.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt binding'):
            prepare.prepare(self.inputs,self.root/'out')

    def test_nested_or_existing_output_rejected(self):
        for output in (self.inputs,self.inputs/'new'):
            with self.assertRaises(ValueError):prepare.prepare(self.inputs,output)


if __name__=='__main__':unittest.main()
