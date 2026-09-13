import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('after_install',Path(__file__).with_name('after_install.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class Tests(unittest.TestCase):
    def fixture(self,work):
        for root in (work/'extracted-xacc/tree/install-xacc',work/'install-xacc'):
            (root/'plugins').mkdir(parents=True);(root/'lib').mkdir()
            (root/'lib/original.so').write_bytes(b'original')
            (root/'plugins/alias.so').symlink_to('../lib/original.so')
        (work/'install-core/lib').mkdir(parents=True)
        (work/'install-core/lib/libvqe.so.1').write_bytes(b'core plugin')
        (work/'install-xacc/plugins/libvqe.so.1').symlink_to('../../install-core/lib/libvqe.so.1')
        receipt={'schema':'qb.core-plugin-normalization/v1','changes':[{
            'path':'install-xacc/plugins/libvqe.so.1','before':'/work/install-core/lib/libvqe.so.1',
            'after':'../../install-core/lib/libvqe.so.1','target_sha256':hashlib.sha256(b'core plugin').hexdigest()}]}
        (work/'plugin-normalization.json').write_text(json.dumps(receipt))
        baseline_inputs(work/'inputs',a.inventory(work/'extracted-xacc/tree/install-xacc'))
    def test_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);self.fixture(work);self.assertTrue(a.audit(work,work/'inputs')['passed'])
    def test_original_change_removal_and_extra(self):
        for action in (lambda w:(w/'install-xacc/lib/original.so').write_bytes(b'changed'),
                       lambda w:(w/'install-xacc/lib/original.so').unlink(),
                       lambda w:(w/'install-xacc/lib/extra').write_bytes(b'extra')):
            with tempfile.TemporaryDirectory() as tmp:
                work=Path(tmp);self.fixture(work);action(work)
                with self.assertRaises(ValueError):a.audit(work,work/'inputs')
    def test_target_hash_or_link(self):
        for change in ('bytes','link'):
            with tempfile.TemporaryDirectory() as tmp:
                work=Path(tmp);self.fixture(work)
                if change=='bytes':(work/'install-core/lib/libvqe.so.1').write_bytes(b'tamper')
                else:
                    link=work/'install-xacc/plugins/libvqe.so.1';link.unlink();link.symlink_to('../../elsewhere')
                with self.assertRaises(ValueError):a.audit(work,work/'inputs')
    def test_unlisted_or_duplicate_receipt(self):
        for duplicate in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                work=Path(tmp);self.fixture(work);path=work/'plugin-normalization.json';receipt=json.loads(path.read_text())
                receipt['changes']=receipt['changes']*2 if duplicate else []
                path.write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):a.audit(work,work/'inputs')


def baseline_inputs(inputs,entries):
    import tarfile,io,json,hashlib
    root=inputs/'xacc';root.mkdir(parents=True)
    converted={}
    for name,entry in entries.items():
        info=dict(entry)
        if info['type']=='link':info={'type':'symlink','target':info['target'],'mode':0o777}
        elif info['type']=='file':info['size']=info.pop('bytes')
        converted['install-xacc/'+name]=info
    raw=json.dumps({'schema':'qb.source-artifact/v1','entries':converted}).encode()
    path=root/'archive.tar.gz'
    with tarfile.open(path,'w:gz') as tar:
        member=tarfile.TarInfo('receipt.json');member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
    (root/'recovered.json').write_text(json.dumps({'output_artifact':{
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,
        'receipt_sha256':hashlib.sha256(raw).hexdigest()}}))

class BindingTests(unittest.TestCase):
    fixture = Tests.fixture
    def test_matching_tampered_baseline_and_derivative_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);self.fixture(work)
            for root in ('install-xacc','extracted-xacc/tree/install-xacc'):
                (work/root/'lib/original.so').write_bytes(b'correlated tamper')
            with self.assertRaisesRegex(ValueError,'baseline mutated'):a.audit(work,work/'inputs')
    def test_archive_and_receipt_hash_bindings(self):
        for field in ('sha256','receipt_sha256'):
            with tempfile.TemporaryDirectory() as tmp:
                work=Path(tmp);self.fixture(work)
                path=work/'inputs/xacc/recovered.json';report=json.loads(path.read_text())
                report['output_artifact'][field]='0'*64;path.write_text(json.dumps(report))
                with self.assertRaises(ValueError):a.original_entries(work/'inputs')
