import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import random
import tempfile
import tarfile
import unittest
from unittest.mock import patch
import zlib

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

reference=load('reference',HERE/'report_reference.py')
guest=load('guest_reference_test',HERE/'guest.py')
fixtures=load('output_fixtures',HERE.parent/'core_output/test_output.py')
output=fixtures.output

class ReferenceTests(unittest.TestCase):
    def fixture(self,root,success=True):
        report,roots=fixtures.OutputTests().fixture(root,success)
        report.update(kind='qb-core-native/v1',protocol_sha256='a'*64,materials_sha256='b'*64)
        archive=root/'output.tar.gz'
        identity=output.pack(archive,report,roots)
        console=reference.envelope(dict(report,output_artifact=identity))
        console.pop('output_artifact')
        return report,archive,identity,console

    def test_success_round_trip_and_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,path,identity,console=self.fixture(Path(tmp))
            verified,full,provenance=reference.resolve(path,identity,console,output)
            self.assertTrue(verified['verified'])
            self.assertEqual(full,dict(report,output_artifact=identity))
            self.assertTrue(provenance['console_artifact_binding'])
            record=reference.recovered_record(full,provenance)
            self.assertTrue(record['console_artifact_binding'])
            self.assertEqual(record['source'],'compact-console-reference')
            self.assertEqual(record['result'],full)
            self.assertEqual(reference.resolve(path,identity,report,output)[1],full)

    def test_native_failure_remains_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,path,identity,console=self.fixture(Path(tmp),False)
            self.assertFalse(console['native_passed'])
            self.assertFalse(reference.resolve(path,identity,console,output)[1]['native_passed'])
            with self.assertRaises(ValueError):reference.resolve(path,identity,dict(console,native_passed=True),output)

    def test_changed_bindings_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,path,identity,console=self.fixture(Path(tmp))
            for field in ('protocol_sha256','materials_sha256'):
                with self.subTest(field=field),self.assertRaises(ValueError):
                    reference.resolve(path,identity,dict(console,**{field:'c'*64}),output)
            for field in ('report_sha256','receipt_sha256','sha256'):
                with self.subTest(field=field),self.assertRaises(ValueError):
                    reference.resolve(path,dict(identity,**{field:'c'*64}),console,output)

    def test_missing_artifact_never_claims_success(self):
        for report in ({'native_passed':True}, {'native_passed':True,'output_artifact':{}},
                       {'native_passed':True,'output_artifact_error':'TimeoutError'}):
            self.assertFalse(reference.envelope(report)['native_passed'])
            self.assertNotIn('output_artifact',reference.envelope(report))

    def test_huge_report_emits_compact_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            report,path,identity,console=self.fixture(root)
            report.update(output_artifact=identity,large=random.Random(9).randbytes(100000).hex())
            helper=root/'inputs/native';helper.mkdir(parents=True)
            (helper/'report_reference.py').write_bytes((HERE/'report_reference.py').read_bytes())
            stream=io.StringIO()
            with patch.object(guest,'ROOT',root),contextlib.redirect_stdout(stream):guest.emit(report)
            lines=stream.getvalue().splitlines();parts=lines[:len(lines)//2]
            encoded=''.join(line.split()[-1] for line in parts)
            self.assertLess(len(encoded),20480)
            decoded=json.loads(zlib.decompress(base64.b64decode(encoded)))
            self.assertEqual(decoded,reference.envelope(report))
            self.assertTrue(decoded['native_passed'])

    def test_duplicate_report_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            report,path,identity,console=self.fixture(root)
            duplicate=root/'duplicate.tar.gz'
            with tarfile.open(path,'r:gz') as source,tarfile.open(duplicate,'w:gz') as target:
                for member in source:
                    target.addfile(member,source.extractfile(member) if member.isfile() else None)
                raw=reference.canonical(report)
                member=tarfile.TarInfo('report.json');member.size=len(raw)
                target.addfile(member,io.BytesIO(raw))
            identity=dict(identity,bytes=duplicate.stat().st_size,sha256=reference.sha(duplicate.read_bytes()))
            with self.assertRaises(ValueError):reference.resolve(duplicate,identity,console,output)

    def test_expanded_archive_bound_before_report_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _,_,identity,console=self.fixture(root)
            path=root/'expanded.tar.gz'
            with tarfile.open(path,'w:gz') as target:
                for name in ('large-one','large-two'):
                    member=tarfile.TarInfo(name);member.size=1024
                    target.addfile(member,io.BytesIO(b'x'*1024))
            identity=dict(identity,bytes=path.stat().st_size,sha256=reference.sha(path.read_bytes()))
            with patch.object(output,'MAX_BYTES',1500),self.assertRaisesRegex(ValueError,'expanded bound'):
                reference.resolve(path,identity,console,output)

    def test_compressed_hash_checked_before_tar_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,path,identity,console=self.fixture(Path(tmp))
            with patch.object(reference.tarfile,'open',side_effect=AssertionError('must not traverse')):
                with self.assertRaisesRegex(ValueError,'archive hash'):
                    reference.resolve(path,dict(identity,sha256='c'*64),console,output)

    def test_special_member_rejected_before_report_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _,_,identity,console=self.fixture(root)
            path=root/'special.tar.gz'
            with tarfile.open(path,'w:gz') as target:
                member=tarfile.TarInfo('device');member.type=tarfile.CHRTYPE
                target.addfile(member)
            identity=dict(identity,bytes=path.stat().st_size,sha256=reference.sha(path.read_bytes()))
            with self.assertRaisesRegex(ValueError,'member type/size'):
                reference.resolve(path,identity,console,output)

    def test_report_read_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,path,identity,console=self.fixture(Path(tmp))
            with patch.object(reference,'MAX_REPORT_BYTES',1),self.assertRaises(ValueError):
                reference.resolve(path,identity,console,output)

if __name__=='__main__':unittest.main()
