"""Prepare or explicitly launch one QPP image VM using the existing supervisor."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time
import tempfile

HERE=Path(__file__).resolve().parent
KEY='native-image-report.json'
OPERATOR_FILES=('core_package/native_image_cloud.py','core_package/native_image_evidence.py',
 'core_package/native_image.py',
 'source_build/run.py','full_decoder/cloud/run.py','gpu_release/supervisor.py',
 'gpu_release/observer.py','gpu_package/console.py','gpu_adapter/console.py',
 'source_artifact/run.py','source_artifact/archive.py')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1024**2):h.update(chunk)
    return h.hexdigest()


def prepare(image_archive,output):
    native=load('cloud_native_image',HERE/'native_image.py')
    output=Path(output);output.mkdir();work=output/'work';work.mkdir()
    prepared=native.prepare(image_archive,work/'native')
    for source,target in [('native_image_cloud_guest.py','guest.py'),('native_image_evidence.py','native_image_evidence.py')]:
        shutil.copyfile(HERE/source,work/target)
    files={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in work.rglob('*') if p.is_file()}
    protocol={'schema':'qb.native-image-cloud-protocol/v1','native_protocol_sha256':prepared['protocol_sha256'],
              'files':files,'operator_files':{name:sha(HERE.parent/name) for name in OPERATOR_FILES},
              'account':'090208085542','region':'us-east-1','instance_type':'m7i.large','root_gib':20,
              'observation_seconds':3600,'cleanup_seconds':300,'executed':False}
    (work/'cloud-protocol.json').write_text(json.dumps(protocol,indent=2,sort_keys=True)+'\n')
    with tarfile.open(output/'cpu.tar.gz','w:gz',dereference=False) as tar:
        for p in sorted(work.iterdir()):tar.add(p,arcname=p.name)
    identity={'bytes':(output/'cpu.tar.gz').stat().st_size,'sha256':sha(output/'cpu.tar.gz')}
    if identity['bytes']>1024**3:raise ValueError('transfer size bound')
    (output/'archive.json').write_text(json.dumps(identity,indent=2)+'\n')
    return dict(identity,cloud_protocol_sha256=sha(work/'cloud-protocol.json'),native_protocol_sha256=prepared['protocol_sha256'],executed=False)


def wrap(original,url,account):
    if not url.startswith('https://') or any(c in url for c in ('\n','\r','"','\\')) or not account.isdigit():raise ValueError('private upload config')
    anchor='python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
    text=original.decode()
    if text.count(anchor)!=1:raise ValueError('bootstrap entrypoint')
    config='url = "'+url+'"\nheader = "x-amz-server-side-encryption: AES256"\nheader = "x-amz-expected-bucket-owner: '+account+'"\n'
    encoded=base64.b64encode(config.encode()).decode()
    replacement="umask 077\nprintf '%s' '"+encoded+"' | base64 -d > /proof/output-put.conf\numask 022\n"+anchor.replace('python3 /work/guest.py','timeout 1500 python3 /work/guest.py')
    result=text.replace(anchor,replacement).replace('qb-xacc-fresh-source-v1','qb-qpp-native-image/v1').encode()
    if len(result)>16384:raise ValueError('userdata size bound')
    return result


def cloud_instance(item,plan):
    expected={'Architecture':'x86_64','InstanceType':'m7i.large','ImageId':plan['image'],
              'SubnetId':plan['subnet'],'VpcId':plan['vpc'],'ClientToken':plan['run']}
    if any(item.get(k)!=v for k,v in expected.items()):raise ValueError('cloud instance identity/platform')
    if {'Key':'QBProofRun','Value':plan['run']} not in item.get('Tags',[]):raise ValueError('cloud instance owner tag')
    return {k:item[k] for k in ('InstanceId',*expected)}


def archived_protocol(archive,expected):
    found=False;total=0
    with tarfile.open(archive,'r|gz') as tar:
        for count,member in enumerate(tar):
            total+=member.size
            if count>=128 or total>1024**3 or not (member.isfile() or member.isdir()):raise ValueError('cloud archive member bounds')
            if member.name=='cloud-protocol.json':
                if found or not member.isfile() or not 0<member.size<=1024**2:raise ValueError('cloud protocol member')
                raw=tar.extractfile(member).read(1024**2+1)
                if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('archive/cloud protocol mismatch')
                found=True
    if not found:raise ValueError('missing archived cloud protocol')


def run_frozen(artifact,directory,archive_sha256,protocol_sha256):
    artifact,directory=Path(artifact),Path(directory)
    if directory.exists():raise ValueError('new state required')
    identity=json.loads((artifact/'archive.json').read_text())
    if sha(artifact/'cpu.tar.gz')!=archive_sha256 or identity['sha256']!=archive_sha256 or (artifact/'cpu.tar.gz').stat().st_size!=identity['bytes']:
        raise ValueError('externally bound transfer archive')
    if sha(artifact/'work/cloud-protocol.json')!=protocol_sha256:raise ValueError('externally bound cloud protocol')
    archived_protocol(artifact/'cpu.tar.gz',protocol_sha256)
    protocol=json.loads((artifact/'work/cloud-protocol.json').read_text())
    if protocol.get('schema')!='qb.native-image-cloud-protocol/v1' or set(protocol['operator_files'])!=set(OPERATOR_FILES):raise ValueError('operator protocol schema')
    for key,value in {'account':'090208085542','region':'us-east-1','instance_type':'m7i.large','root_gib':20,'observation_seconds':3600,'cleanup_seconds':300}.items():
        if protocol.get(key)!=value:raise ValueError('fixed cloud resource scope')
    for name,expected in protocol['operator_files'].items():
        if sha(HERE.parent/name)!=expected:raise ValueError('operator tool identity')
    source=load('qpp_cloud_source',HERE.parent/'source_build/run.py');lifecycle=source.lifecycle
    evidence=load('qpp_cloud_evidence',HERE/'native_image_evidence.py')
    transport=load('qpp_cloud_retention_deadline',HERE.parent/'source_artifact/run.py')
    import boto3
    from botocore.config import Config
    client=boto3.client('s3',region_name=lifecycle.REGION,config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':2},signature_version='s3v4'))
    original_aws=lifecycle.aws;context={}
    lifecycle.UPLOAD_TIMEOUT=600;lifecycle.SupervisorBase=lifecycle.Supervisor
    def aws(service,operation,params):
        if service=='s3api' and operation=='delete-bucket':
            state=directory/'retention.json'
            retained=json.loads(state.read_text()) if state.exists() else {}
            if not retained.get('verified'):raise RuntimeError('output_bucket_retained_for_recovery')
            original_aws('s3api','delete-object',{'Bucket':params['Bucket'],'Key':KEY,'ExpectedBucketOwner':lifecycle.ACCOUNT})
        result=original_aws(service,operation,params)
        if service=='s3api' and operation=='put-object':context['bucket']=params['Bucket']
        return result
    def bootstrap(url,digest):
        upload=client.generate_presigned_url('put_object',Params={'Bucket':context['bucket'],'Key':KEY,
            'ExpectedBucketOwner':lifecycle.ACCOUNT,'ServerSideEncryption':'AES256'},ExpiresIn=3600)
        return wrap(source.bootstrap(url,digest),upload,lifecycle.ACCOUNT)
    class Supervisor(source.SourceSupervisor):
        def observe(self,**kwargs):
            super().observe(**kwargs)
            transfer=json.loads((directory/'transfer.json').read_text())
            reference=json.loads((directory/'vm/recovered.json').read_text())['result']
            retained={'verified':False,'bucket':transfer['bucket'],'key':KEY,'account':lifecycle.ACCOUNT,
                      'cloud_protocol_sha256':protocol_sha256,'native_passed':False}
            try:
                if reference.get('kind')!='qb-qpp-native-image/v1' or reference.get('protocol_sha256')!=protocol['native_protocol_sha256']:raise ValueError('console protocol reference')
                expected=reference['output_artifact']
                if type(expected.get('bytes')) is not int or not 0<expected['bytes']<=2*1024**2:raise ValueError('report size')
                with transport.retention_deadline(self.deadline('observe_until')):
                    response=client.get_object(Bucket=transfer['bucket'],Key=KEY,ExpectedBucketOwner=lifecycle.ACCOUNT)
                    with response['Body'] as body:
                        if response['ContentLength']!=expected['bytes']:raise ValueError('response size')
                        raw=body.read(2*1024**2+1)
                    if len(raw)!=expected['bytes'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:raise ValueError('downloaded report identity')
                    path=directory/'native-image-report.json'
                    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                    verified=evidence.verify(path,expected,protocol['native_protocol_sha256'])
                retained['verified']=True;retained['result']={'classification':verified['classification'],'envelope_sha256':verified['envelope_sha256']}
                item=self.discover('observe_until')
                if item is None:raise ValueError('native instance unavailable')
                retained['cloud_instance']=cloud_instance(item,self.state['plan'])
                retained['native_passed']=verified['classification']['native_passed'] and reference.get('native_passed') is True
                if not retained['native_passed']:raise RuntimeError('native image tests failed')
            except Exception as error:
                retained['error']=type(error).__name__
                raise RuntimeError('native_image_retention_or_test_failed') from None
            finally:lifecycle.atomic_json(directory/'retention.json',retained)
    lifecycle.aws=aws;lifecycle.bootstrap=bootstrap;lifecycle.Supervisor=Supervisor
    old_args=sys.argv
    try:
        sys.argv=['native_image_cloud.py',str(artifact),str(directory)]
        code=lifecycle.main()
    finally:sys.argv=old_args
    return code


def run(artifact,directory,archive_sha256,protocol_sha256):
    artifact=Path(artifact)
    native=load('cloud_private_snapshot',HERE/'native_image.py')
    with tempfile.TemporaryDirectory(prefix='qpp-cloud-inputs-') as tmp:
        private=Path(tmp);(private/'work').mkdir()
        copied=native.snapshot(artifact/'cpu.tar.gz',private/'cpu.tar.gz',1024**3)
        if copied['sha256']!=archive_sha256:raise ValueError('externally bound transfer archive')
        copied=native.snapshot(artifact/'work/cloud-protocol.json',private/'work/cloud-protocol.json',1024**2)
        if copied['sha256']!=protocol_sha256:raise ValueError('externally bound cloud protocol')
        native.snapshot(artifact/'archive.json',private/'archive.json',4096)
        return run_frozen(private,directory,archive_sha256,protocol_sha256)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('prepare');a.add_argument('image_archive',type=Path);a.add_argument('output',type=Path)
    a=sub.add_parser('run');a.add_argument('artifact',type=Path);a.add_argument('directory',type=Path)
    a.add_argument('--archive-sha256',required=True);a.add_argument('--protocol-sha256',required=True)
    args=vars(p.parse_args());action=args.pop('action')
    if action=='prepare':print(json.dumps(prepare(**args)))
    else:raise SystemExit(run(**args))
