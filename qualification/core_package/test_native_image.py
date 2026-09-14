import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import native_image as n


class NativeImageTests(unittest.TestCase):
    def test_snapshot_identity_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'input';p.write_bytes(b'exact')
            expected={'bytes':5,'sha256':hashlib.sha256(b'exact').hexdigest()}
            self.assertEqual(n.snapshot(p,root/'copy',5,expected),expected)
            p.write_bytes(b'other')
            with self.assertRaises(ValueError):n.snapshot(p,root/'bad',5,expected)
            (root/'link').symlink_to(p)
            with self.assertRaises(OSError):n.snapshot(root/'link',root/'linked',5)

    def test_loaded_identity_index_or_config_and_complete_runtime_match(self):
        proof={'image_index_digest':'sha256:index','config_digest':'sha256:config'}
        config={'config':{'User':'65532','Env':['SAFE=1']},'rootfs':{'diff_ids':['sha256:layer']}}
        item={'Id':proof['config_digest'],'Architecture':'amd64','Os':'linux',
              'Config':config['config'],'RootFS':{'Type':'layers','Layers':config['rootfs']['diff_ids']}}
        for identity in proof.values():
            good=copy.deepcopy(item);good['Id']=identity
            self.assertEqual(n.loaded_matches([good],config,proof),identity)
        for field,value in [('Id','sha256:other'),('Architecture','arm64'),
                            ('Config',{'User':'0','Env':['SAFE=1']}),
                            ('RootFS',{'Type':'layers','Layers':['sha256:other']})]:
            bad=copy.deepcopy(item);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):n.loaded_matches([bad],config,proof)
        bad=copy.deepcopy(item);bad['Config']['Healthcheck']={'Test':['CMD','unexpected']}
        with self.assertRaises(ValueError):n.loaded_matches([bad],config,proof)

    def test_wrong_host_or_docker_override_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            with mock.patch.object(n.platform,'system',return_value='Darwin'):
                with self.assertRaises(ValueError):n.execute(Path(tmp),out,'0'*64)
            self.assertFalse(out.exists())
            with mock.patch.object(n.platform,'system',return_value='Linux'),mock.patch.object(n.platform,'machine',return_value='x86_64'),mock.patch.dict(n.os.environ,{'DOCKER_HOST':'ssh://remote'}):
                with self.assertRaises(ValueError):n.execute(Path(tmp),out,'0'*64)
            self.assertFalse(out.exists())

    def test_bad_protocol_retains_failure_before_any_docker_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'protocol.json').write_text('{}')
            with mock.patch.object(n.platform,'system',return_value='Linux'),mock.patch.object(n.platform,'machine',return_value='x86_64'),mock.patch.dict(n.os.environ,{'DOCKER_HOST':'','DOCKER_CONTEXT':''}):
                report=n.execute(root,root/'out','0'*64)
            self.assertFalse(report['passed']);self.assertEqual(report['commands'],[])
            self.assertIn('external identity',report['error'])
            self.assertFalse(report['cloud_instance_binding_verified'])
            self.assertEqual(json.loads((root/'out/execution.json').read_text()),report)

if __name__=='__main__':unittest.main()
