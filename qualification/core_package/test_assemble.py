import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('tested_assembly',Path(__file__).with_name('assemble.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AssemblyTests(unittest.TestCase):
    def fixture(self,root):
        staged=root/'staged';staged.mkdir()
        for name in ('work.tar','runtime/qpp_runtime.py','runtime/requirements.txt','runtime/install-python.sh','python/wheels/example.whl'):
            target=staged/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('fixture '+name).encode())
        receipt={'schema':'qb.core-staged-inputs/v1','staged':True,
                 'inventory':a.STAGE.context_inventory(staged),
                 'evidence_provenance':{'console_artifact_binding':False}}
        (staged/'staging.json').write_text(json.dumps(receipt))
        digest=hashlib.sha256((staged/'staging.json').read_bytes()).hexdigest()
        os_inputs=root/'os';(os_inputs/'debs').mkdir(parents=True)
        (os_inputs/'debs/example.deb').write_bytes(b'package')
        lock={'packages':[{'file':'example.deb','bytes':7,'sha256':hashlib.sha256(b'package').hexdigest()}],
              'installed':False,'resolver_completeness_verified':False}
        return staged,os_inputs,root/'output',digest,lock
    def call(self,values):
        with patch.object(a.OS,'audit',return_value=values[-1]):return a.assemble(*values[:-1])
    def test_bound_success_retains_unqualified_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            values=self.fixture(Path(tmp));result=self.call(values)
            self.assertTrue(result['assembled'])
            for key in ('built','runtime_qualified','redistribution_cleared'):self.assertFalse(result[key])
            self.assertEqual(result['staging_sha256'],values[3])
            self.assertFalse(result['evidence_provenance']['console_artifact_binding'])
            self.assertEqual((values[2]/'work.tar').read_bytes(),(values[0]/'work.tar').read_bytes())
    def test_wrong_expected_hash_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            values=list(self.fixture(Path(tmp)));values[3]='0'*64
            with self.assertRaisesRegex(ValueError,'staging receipt identity'):self.call(values)
            self.assertFalse(values[2].exists())
    def test_changed_payload_rejected_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            values=self.fixture(Path(tmp));(values[0]/'work.tar').write_bytes(b'changed')
            with self.assertRaises(ValueError):self.call(values)
            self.assertFalse(values[2].exists())
    def test_correlated_manifest_payload_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            values=self.fixture(Path(tmp));staged=values[0]
            (staged/'work.tar').write_bytes(b'changed')
            receipt=json.loads((staged/'staging.json').read_text())
            receipt['inventory']['work.tar'].update(bytes=7,sha256=hashlib.sha256(b'changed').hexdigest())
            (staged/'staging.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'staging receipt identity'):self.call(values)
    def test_changed_deb_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            values=self.fixture(Path(tmp));(values[1]/'debs/example.deb').write_bytes(b'changed')
            with self.assertRaises(ValueError):self.call(values)
            self.assertFalse(values[2].exists())
