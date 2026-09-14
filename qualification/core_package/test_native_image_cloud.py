import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import native_image_cloud as cloud


class CloudProtocolTests(unittest.TestCase):
    def test_wrap_keeps_endpoint_out_of_plaintext_and_bounds_userdata(self):
        original=b'#!/bin/bash\nset -eu\npython3 /work/guest.py >/dev/console 2>/proof/guest.stderr\n'
        url='https://private.example.invalid/report?X-Amz-Signature=fixture-only'
        wrapped=cloud.wrap(original,url,'090208085542')
        self.assertLessEqual(len(wrapped),16384)
        self.assertNotIn(url.encode(),wrapped)
        encoded=re.search(rb"printf '%s' '([A-Za-z0-9+/=]+)'",wrapped).group(1)
        config=base64.b64decode(encoded).decode()
        self.assertIn('url = "'+url+'"',config)
        self.assertIn('x-amz-server-side-encryption: AES256',config)
        self.assertIn('x-amz-expected-bucket-owner: 090208085542',config)
        self.assertIn(b'umask 077\n',wrapped)
        self.assertEqual(wrapped.count(b'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'),1)
        for bad in ('http://example.invalid','https://example.invalid\nsecret','https://example.invalid"','https://example.invalid\\'):
            with self.subTest(url=bad),self.assertRaises(ValueError):cloud.wrap(original,bad,'090208085542')
        for bad in (b'no anchor',original+original,b'x'*17000+original):
            with self.assertRaises(ValueError):cloud.wrap(bad,url,'090208085542')

    def fixture_instance(self):
        plan={'image':'ami-0123456789abcdef0','subnet':'subnet-0123456789abcdef0','vpc':'vpc-0123456789abcdef0','run':'qb-proof-fixture'}
        item={'InstanceId':'i-0123456789abcdef0','Architecture':'x86_64','InstanceType':'m7i.large',
              'ImageId':plan['image'],'SubnetId':plan['subnet'],'VpcId':plan['vpc'],'ClientToken':plan['run'],
              'Tags':[{'Key':'QBProofRun','Value':plan['run']}]}
        return item,plan

    def test_cloud_instance_exact_identity_architecture_and_ownership(self):
        item,plan=self.fixture_instance();result=cloud.cloud_instance(item,plan)
        self.assertEqual(result['InstanceId'],item['InstanceId'])
        for field in ('Architecture','InstanceType','ImageId','SubnetId','VpcId','ClientToken'):
            bad=copy.deepcopy(item);bad[field]='different'
            with self.subTest(field=field),self.assertRaises(ValueError):cloud.cloud_instance(bad,plan)
        for tags in ([],[{'Key':'QBProofRun','Value':'other'}]):
            bad=copy.deepcopy(item);bad['Tags']=tags
            with self.assertRaises(ValueError):cloud.cloud_instance(bad,plan)

    def fixture_artifact(self,root,*,different_embedded=False):
        root.mkdir();(root/'work').mkdir()
        protocol={'schema':'qb.native-image-cloud-protocol/v1','native_protocol_sha256':'a'*64,'files':{},
                  'operator_files':{name:cloud.sha(cloud.HERE.parent/name) for name in cloud.OPERATOR_FILES},
                  'account':'090208085542','region':'us-east-1','instance_type':'m7i.large','root_gib':20,
                  'observation_seconds':3600,'cleanup_seconds':300,'executed':False}
        raw=json.dumps(protocol,sort_keys=True).encode();(root/'work/cloud-protocol.json').write_bytes(raw)
        embedded=b'{"different":"protocol"}' if different_embedded else raw
        with tarfile.open(root/'cpu.tar.gz','w:gz') as tar:
            member=tarfile.TarInfo('cloud-protocol.json');member.size=len(embedded);tar.addfile(member,io.BytesIO(embedded))
        identity={'bytes':(root/'cpu.tar.gz').stat().st_size,'sha256':cloud.sha(root/'cpu.tar.gz')}
        (root/'archive.json').write_text(json.dumps(identity))
        return identity['sha256'],hashlib.sha256(raw).hexdigest()

    def test_bad_external_archive_or_protocol_never_loads_resource_operator(self):
        for mismatch in ('archive','protocol'):
            with self.subTest(mismatch=mismatch),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);a,p=self.fixture_artifact(root/'artifact')
                with patch.object(cloud,'load',side_effect=AssertionError('resource operator must not load')) as load:
                    with self.assertRaises(ValueError):cloud.run_frozen(root/'artifact',root/'state','0'*64 if mismatch=='archive' else a,'0'*64 if mismatch=='protocol' else p)
                load.assert_not_called();self.assertFalse((root/'state').exists())

    def test_mismatched_embedded_protocol_rejected_before_operator_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a,p=self.fixture_artifact(root/'artifact',different_embedded=True)
            with patch.object(cloud,'load',side_effect=AssertionError('resource operator must not load')) as load:
                with self.assertRaises(ValueError):cloud.run_frozen(root/'artifact',root/'state',a,p)
            load.assert_not_called();self.assertFalse((root/'state').exists())

    def test_mocked_retention_precedes_deletion_and_failed_verification_keeps_bucket(self):
        from contextlib import nullcontext
        import types
        for valid in (True,False):
            with self.subTest(valid=valid),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);a,p=self.fixture_artifact(root/'artifact');state=root/'state'
                operations=[];raw=b'{}';artifact={'bytes':2,'sha256':hashlib.sha256(raw).hexdigest()}
                item,plan=self.fixture_instance()
                class Base:
                    def __init__(self):self.state={'plan':plan}
                    def observe(self,**kwargs):operations.append('observe')
                    def deadline(self,phase):return 9999999999
                    def discover(self,phase):return item
                def original_aws(service,operation,params):operations.append(operation);return {}
                def atomic(path,data):path.write_text(json.dumps(data))
                lifecycle=types.SimpleNamespace(REGION='us-east-1',ACCOUNT='090208085542',Supervisor=Base,aws=original_aws,atomic_json=atomic)
                def main():
                    state.mkdir();(state/'vm').mkdir()
                    (state/'transfer.json').write_text(json.dumps({'bucket':'fixture-bucket'}))
                    reference={'kind':'qb-qpp-native-image/v1','protocol_sha256':'a'*64,'output_artifact':artifact,'native_passed':True}
                    (state/'vm/recovered.json').write_text(json.dumps({'result':reference}))
                    supervisor=lifecycle.Supervisor()
                    try:supervisor.observe()
                    except RuntimeError:operations.append('observe-failed')
                    try:lifecycle.aws('s3api','delete-bucket',{'Bucket':'fixture-bucket'})
                    except RuntimeError:operations.append('bucket-retained')
                    return 0
                lifecycle.main=main
                source=types.SimpleNamespace(lifecycle=lifecycle,SourceSupervisor=Base)
                def verify(*args):
                    operations.append('verified' if valid else 'verification-failed')
                    if not valid:raise ValueError('invalid evidence')
                    return {'classification':{'native_passed':True},'envelope_sha256':artifact['sha256']}
                evidence=types.SimpleNamespace(verify=verify)
                transport=types.SimpleNamespace(retention_deadline=lambda deadline:nullcontext())
                def load(name,path):
                    return {'qpp_cloud_source':source,'qpp_cloud_evidence':evidence,'qpp_cloud_retention_deadline':transport}[name]
                def get_object(**kwargs):
                    self.assertEqual(kwargs['ExpectedBucketOwner'],'090208085542')
                    operations.append('get-object');return {'Body':io.BytesIO(raw),'ContentLength':len(raw)}
                client=types.SimpleNamespace(get_object=get_object)
                boto=types.ModuleType('boto3');boto.client=lambda *a,**k:client
                botocore=types.ModuleType('botocore');config=types.ModuleType('botocore.config');config.Config=lambda **kwargs:object()
                with patch.object(cloud,'load',side_effect=load),patch.dict('sys.modules',{'boto3':boto,'botocore':botocore,'botocore.config':config}):
                    self.assertEqual(cloud.run_frozen(root/'artifact',state,a,p),0)
                retained=json.loads((state/'retention.json').read_text())
                self.assertIs(retained['verified'],valid)
                if valid:
                    self.assertTrue(retained['native_passed'])
                    self.assertLess(operations.index('verified'),operations.index('delete-object'))
                    self.assertLess(operations.index('delete-object'),operations.index('delete-bucket'))
                    self.assertEqual(retained['cloud_instance']['Architecture'],'x86_64')
                else:
                    self.assertIn('bucket-retained',operations)
                    self.assertNotIn('delete-object',operations);self.assertNotIn('delete-bucket',operations)


if __name__=='__main__':unittest.main()
