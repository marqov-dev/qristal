import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('os_lock',Path(__file__).with_name('os_lock.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def fixture(self,root):
        for n in ('lists','indexes','debs'):(root/n).mkdir()
        (root/'ubuntu-archive-keyring.gpg').write_bytes(b'key')
        for n in ('base-status','after-status'):(root/n).write_text('Package: base\nVersion: 1\nArchitecture: amd64\nStatus: install ok installed\n')
        (root/'debs/example.deb').write_bytes(b'deb')
        for suite in m.SUITES:
            entries=[]
            for component in ('main','universe'):
                raw=('Package: example\nVersion: 1\nArchitecture: amd64\nFilename: pool/e/example.deb\nSize: 3\nSHA256: '+m.sha(b'deb')+'\n').encode()
                path=root/'indexes'/(m.PREFIX+suite+'_'+component+'_binary-amd64_Packages.lz4.gz')
                path.write_bytes(gzip.compress(raw))
                entries.append(' '+m.sha(raw)+' '+str(len(raw))+' '+component+'/binary-amd64/Packages')
            (root/'lists'/(m.PREFIX+suite+'_InRelease')).write_text('Suite: '+suite+'\nCodename: jammy\nSHA256:\n'+'\n'.join(entries)+'\n')
    def run_audit(self,root):
        with patch.object(m,'KEY_SHA',m.sha(b'key')),patch.object(m,'signed_release',side_effect=lambda raw,key:raw.decode()):return m.audit(root)
    def test_authenticated_relative_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);r=self.run_audit(root)
            self.assertEqual(len(r['packages']),1);self.assertFalse(r['resolver_completeness_verified']);self.assertFalse(r['installed'])
    def test_corruption_fails(self):
        for target in ('debs/example.deb','base-status','ubuntu-archive-keyring.gpg'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.fixture(root);(root/target).write_bytes(b'bad')
                with self.assertRaises(ValueError):self.run_audit(root)
    def test_index_identity_and_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);p=next((root/'indexes').iterdir());p.write_bytes(gzip.compress(b'bad'))
            with self.assertRaises(ValueError):self.run_audit(root)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);p=next((root/'indexes').iterdir());p.rename(root/'indexes/wrong.gz')
            with self.assertRaises(ValueError):self.run_audit(root)
    def test_duplicate_control_and_claims(self):
        with self.assertRaises(ValueError):list(m.records('Package: a\nPackage: b\n'))
        claim=' '+('a'*64)+' 1 main/binary-amd64/Packages\n'
        with self.assertRaises(ValueError):m.claims('Suite: jammy\nCodename: jammy\nSHA256:\n'+claim+claim,'jammy')
    def test_signature_failure(self):
        with patch.object(m.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaises(ValueError):m.signed_release(b'bad',b'key')
            args=run.call_args
            self.assertIn('--homedir',args.args[0]);self.assertIn('--keyring',args.args[0]);self.assertEqual(args.kwargs['timeout'],30)
