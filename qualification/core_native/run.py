"""One bounded Core CPU VM; retain success or failure evidence before cleanup."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def wrap(original,url,account,deadline):
    if any(c in url for c in ('\n','\r','"','\\')) or not url.startswith('https://') or not account.isdigit():
        raise ValueError('invalid private upload configuration')
    anchor='python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
    text=original.decode()
    if text.count(anchor)!=1:raise ValueError('bootstrap entrypoint')
    config='url = "'+url+'"\nheader = "x-amz-server-side-encryption: AES256"\nheader = "x-amz-expected-bucket-owner: '+account+'"\n'
    encoded=base64.b64encode(config.encode()).decode()
    replacement="umask 077\nprintf '%s' '"+encoded+"' | base64 -d > /proof/output-put.conf\numask 022\nCORE_DEADLINE="+str(int(deadline))+' '+anchor
    result=text.replace(anchor,replacement).replace('qb-xacc-fresh-source-v1','qb-core-native/v1').encode()
    if len(result)>16384:raise ValueError('userdata bound')
    return result


def main():
    if len(sys.argv)!=3:raise SystemExit('usage: run.py PREPARED_ARTIFACT NEW_STATE')
    artifact,directory=map(Path,sys.argv[1:])
    # Before any resource creation, reject mismatched runner/native identities.
    output=load('core_output',HERE.parent/'core_output/output.py')
    protocol=json.loads((artifact/'work/protocol.json').read_text())
    for relative,expected in protocol['operator_files'].items():
        if output.digest((HERE.parent/relative).read_bytes())!=expected:raise ValueError('operator source identity')
    source=load('core_source_lifecycle',HERE.parent/'source_build/run.py')
    transport=load('core_retention_transport',HERE.parent/'source_artifact/run.py')
    transport.verify=output.verify
    transport.MAX_BYTES=output.MAX_BYTES
    lifecycle=source.lifecycle
    import boto3
    from botocore.config import Config
    client=boto3.client('s3',region_name=lifecycle.REGION,
        config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':2},signature_version='s3v4'))
    original_aws=lifecycle.aws
    lifecycle.UPLOAD_TIMEOUT=600
    lifecycle.SupervisorBase=lifecycle.Supervisor
    context={}
    def aws(service,operation,params):
        if service=='s3api' and operation=='create-bucket':
            lifecycle.atomic_json(directory/'protocol-identity.json',{
                'protocol_sha256':output.digest((artifact/'work/protocol.json').read_bytes()),
                'operator_files':protocol['operator_files']})
        if service=='s3api' and operation=='delete-bucket':
            p=directory/'retention.json'
            retained=json.loads(p.read_text()) if p.exists() else {}
            if not retained.get('verified'):raise RuntimeError('output_bucket_retained_for_recovery')
            original_aws('s3api','delete-object',{'Bucket':params['Bucket'],'Key':'source-output.tar.gz','ExpectedBucketOwner':lifecycle.ACCOUNT})
        result=original_aws(service,operation,params)
        if service=='s3api' and operation=='put-object':context['bucket']=params['Bucket']
        return result
    def bootstrap(url,digest):
        return wrap(source.bootstrap(url,digest),transport.sign_put(client,context['bucket'],lifecycle.ACCOUNT),lifecycle.ACCOUNT,time.time()+3500)
    class Supervisor(source.SourceSupervisor):
        def observe(self,**kwargs):
            super().observe(**kwargs)
            state=json.loads((directory/'transfer.json').read_text())
            report=json.loads((directory/'vm/recovered.json').read_text())['result']
            retained={'bucket':state['bucket'],'key':'source-output.tar.gz','account':state['account'],'verified':False}
            try:
                deadline=self.deadline('observe_until')
                with transport.retention_deadline(deadline):
                    retained.update(transport.download(client,state,directory,report,deadline=deadline))
                    checker=load('core_result_checker',HERE/'check_result.py')
                    retained['native']=checker.classify(report,artifact/'work/protocol.json',directory/'output.tar.gz')
            except Exception as error:
                retained['error']=type(error).__name__
                raise RuntimeError('core_retention_failed') from None
            finally:lifecycle.atomic_json(directory/'retention.json',retained)
    lifecycle.aws=aws;lifecycle.bootstrap=bootstrap;lifecycle.Supervisor=Supervisor
    code=lifecycle.main()
    p=directory/'retention.json'
    retained=json.loads(p.read_text()) if p.exists() else {}
    return code or (0 if retained.get('native',{}).get('native_passed') else 1)


if __name__=='__main__':sys.exit(main())
