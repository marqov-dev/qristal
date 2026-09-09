import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from bounded_process import capture
from preparation_binding import assemble,verify,validate_prepared_result,BindingError

PROGRAM=b'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[0]; measure q -> c;'
OPTIONS=b'{"qubits":2,"shots":17,"seed":42}'
# Deliberately synthetic lock/policy to test binding, not registry qualification.
LOCK=b'local fixture lock; not a registered dependency artifact'
POLICY={'image_sha256':'a'*64,'dependency_lock_sha256':hashlib.sha256(LOCK).hexdigest()}


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.files,self.manifest=assemble(PROGRAM,OPTIONS,LOCK,backend='qpp',policy=POLICY)
        self.restore()

    def restore(self):
        for p in self.directory.iterdir():p.unlink()
        for name,raw in self.files.items():(self.directory/name).write_bytes(raw)

    def test_roundtrip_and_result(self):
        files,_=verify(self.directory,self.manifest,backend='qpp',policy=POLICY)
        # Use the verified snapshot, not a mutable staged path, for execution.
        with tempfile.TemporaryDirectory() as scratch:
            path=Path(scratch)/'verified.qasm';path.write_bytes(files['canonical.qasm'])
            code,out,err=capture([sys.executable,'/opt/qristal/runtime.py','--qasm',str(path),'--shots','17'])
        self.assertFalse(err)
        result=validate_prepared_result(self.directory,self.manifest,out,returncode=code,backend='qpp',policy=POLICY)
        self.assertEqual(dict(result.counts),{'10':17})
        (self.directory/'options.json').write_bytes(OPTIONS.replace(b'42',b'43'))
        with self.assertRaises(BindingError):validate_prepared_result(self.directory,self.manifest,out,returncode=code,backend='qpp',policy=POLICY)

    def test_artifact_changes(self):
        for name in self.files:
            self.restore();(self.directory/name).write_bytes(self.files[name]+b' ')
            with self.subTest(name=name),self.assertRaises(BindingError):verify(self.directory,self.manifest,backend='qpp',policy=POLICY)
        self.restore();p=self.directory/'canonical.qasm';p.unlink();p.symlink_to(self.directory/'original.qasm')
        with self.assertRaises(BindingError):verify(self.directory,self.manifest,backend='qpp',policy=POLICY)
        self.restore();(self.directory/'unexpected').write_bytes(b'x')
        with self.assertRaises(BindingError):verify(self.directory,self.manifest,backend='qpp',policy=POLICY)

    def test_manifest_changes(self):
        original=json.loads(self.manifest)
        changes=[{'logical_bits':['q[1]','q[0]']},{'backend':'aer'},
                 {'settings':{'qubits':2,'shots':17,'seed':43}},
                 {'settings':{'qubits':2,'shots':17.0,'seed':42}}, {'local_only':1},
                 {'parser':{'qiskit_terra':'other','guard_sha256':'b'*64}},
                 {'policy':POLICY|{'image_sha256':'b'*64}},
                 {'artifacts':original['artifacts']|{'original.qasm':'b'*64}}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(BindingError):
                verify(self.directory,json.dumps(original|change).encode(),backend='qpp',policy=POLICY)
        duplicate=self.manifest.replace(b'"local_only":true',b'"local_only":true,"local_only":true')
        with self.assertRaises(BindingError):verify(self.directory,duplicate,backend='qpp',policy=POLICY)

    def test_self_consistent_tampering_still_needs_expected_facts(self):
        # Original and canonical files changed together cannot match the retained manifest.
        files,_=assemble(PROGRAM.replace(b'q[0]; measure',b'q[1]; measure'),OPTIONS,LOCK,backend='qpp',policy=POLICY)
        for name,raw in files.items():(self.directory/name).write_bytes(raw)
        with self.assertRaises(BindingError):verify(self.directory,self.manifest,backend='qpp',policy=POLICY)

    def test_failed_outputs(self):
        for code,out in [(0,b''),(-9,b''),(0,b'x'*131074)]:
            with self.subTest(code=code,size=len(out)),self.assertRaises(BindingError):
                validate_prepared_result(self.directory,self.manifest,out,returncode=code,backend='qpp',policy=POLICY)

if __name__=='__main__':unittest.main()
