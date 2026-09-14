import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_native_image_probe as fixture
spec=importlib.util.spec_from_file_location('native_image_evidence',Path(__file__).with_name('native_image_evidence.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

class EvidenceTests(unittest.TestCase):
    def fixture(self,root,passed=True,image=None):
        image=image or e.CONFIG
        protocol={'schema':'qb.native-image-protocol/v1','image_index_digest':e.IMAGE,'config_digest':e.CONFIG,
                  'files':{'image.tar':{'bytes':e.ARCHIVE_BYTES,'sha256':e.ARCHIVE_SHA}}}
        protocol_path=root/'protocol.json';protocol_path.write_text(json.dumps(protocol));protocol_sha=e.sha(protocol_path.read_bytes())
        results=root/'results';results.mkdir()
        report={'schema':'qb.native-image-execution/v1','passed':passed,'protocol_sha256':protocol_sha,
                'hosted':False,'redistribution_cleared':False,'cloud_instance_binding_verified':False,'resource_cleanup_verified':False}
        if passed:
            mock=fixture.NativeTests();mock.setUp()
            with patch.object(fixture,'IMAGE',image):probe=mock.run_probe(root)
            self.assertTrue(probe['passed'])
            (results/'probes.local-probe.json').write_bytes((root/'result.local-probe.json').read_bytes())
            probe['local_receipt']['filename']='probes.local-probe.json'
            (results/'probes.json').write_text(json.dumps(probe))
            report.update(probe=probe,execution_digest=image,host_architecture='x86_64',engine_platform='linux x86_64',empty_daemon_observed_before_load=True,
                archive_verification={'image_index_digest':e.IMAGE,'config_digest':e.CONFIG,'archive_sha256':e.ARCHIVE_SHA,'archive_bytes':e.ARCHIVE_BYTES,'layer_diff_ids_verified':True})
        else:report['error']='retained diagnostic π\n'
        (results/'execution.json').write_text(json.dumps(report,ensure_ascii=False))
        return results,protocol_path,protocol_sha,report

    def verify(self,root,results,protocol_path,protocol_sha):
        path=root/'envelope.json';identity=e.pack(results,protocol_path,path)
        return e.verify(path,identity,protocol_sha)

    def test_success_both_image_id_forms_and_scope(self):
        for image in (e.IMAGE,e.CONFIG):
            with self.subTest(image=image),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();results,protocol,psha,_=self.fixture(root,image=image)
                verified=self.verify(root,results,protocol,psha)
                self.assertTrue(verified['classification']['native_passed'])
                self.assertFalse(verified['classification']['cloud_instance_binding_verified'])
                self.assertEqual(verified['files']['execution.json'],(results/'execution.json').read_bytes())

    def test_failure_diagnostics_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();results,protocol,psha,report=self.fixture(root,False)
            verified=self.verify(root,results,protocol,psha)
            self.assertFalse(verified['classification']['native_passed'])
            self.assertEqual(verified['execution'],report)

    def test_external_identity_and_protocol_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();results,protocol,psha,_=self.fixture(root,False)
            path=root/'envelope.json';identity=e.pack(results,protocol,path)
            with self.assertRaises(ValueError):e.verify(path,dict(identity,sha256='a'*64),psha)
            with self.assertRaises(ValueError):e.verify(path,identity,'a'*64)

    def test_changed_internal_hash_duplicate_and_wrong_file_set(self):
        for change in ('hash','duplicate','file'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();results,protocol,psha,_=self.fixture(root,False)
                path=root/'envelope.json';e.pack(results,protocol,path);data=json.loads(path.read_text())
                if change=='hash':data['files']['execution.json']['sha256']='a'*64
                if change=='file':data['files']['../execution.json']=data['files'].pop('execution.json')
                raw=json.dumps(data).encode()
                if change=='duplicate':raw=raw.replace(b'"files":',b'"files":{},"files":',1)
                path.write_bytes(raw)
                with self.assertRaises(ValueError):e.verify(path,{'bytes':len(raw),'sha256':e.sha(raw)},psha)

    def test_missing_probes_wrong_archive_or_native_claim_fail(self):
        for change in ('missing','image','archive','protocol','host','cleanup','imports'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();results,protocol,psha,report=self.fixture(root)
                if change=='missing':(results/'probes.json').unlink()
                elif change=='image':report['execution_digest']='sha256:'+'a'*64
                elif change=='archive':report['archive_verification']['archive_sha256']='a'*64
                elif change=='protocol':report['protocol_sha256']='a'*64
                else:
                    probe=report['probe']
                    if change=='host':probe['native_host_observed']=False
                    elif change=='cleanup':probe['cases'][0]['cleanup']['absence_verified']=False
                    elif change=='imports':probe['cases']=probe['cases'][:2]
                    (results/'probes.json').write_text(json.dumps(probe))
                (results/'execution.json').write_text(json.dumps(report))
                with self.assertRaises(ValueError):self.verify(root,results,protocol,psha)

    def test_failed_execution_still_rejects_duplicate_probe_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();results,protocol,psha,_=self.fixture(root,False)
            (results/'probes.json').write_text('{"schema":"qb.qpp-native-host-probe/v1","passed":false,"passed":true}')
            with self.assertRaises(ValueError):self.verify(root,results,protocol,psha)

    def test_pack_bounds_symlink_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();results,protocol,_,_=self.fixture(root,False);path=root/'envelope.json'
            e.pack(results,protocol,path)
            with self.assertRaises(FileExistsError):e.pack(results,protocol,path)
            (results/'unexpected').write_text('x')
            with self.assertRaises(ValueError):e.pack(results,protocol,root/'other')
            (results/'unexpected').unlink();(results/'execution.json').unlink();(results/'execution.json').symlink_to(protocol)
            with self.assertRaises(ValueError):e.pack(results,protocol,root/'other')
            (results/'execution.json').unlink();(results/'execution.json').write_bytes(b'x'*(e.MAX_BYTES+1))
            with self.assertRaises(ValueError):e.pack(results,protocol,root/'other')

if __name__=='__main__':unittest.main()
