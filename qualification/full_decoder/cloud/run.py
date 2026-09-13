"""One bounded CPU VM qualification, with private transfer and verified cleanup.

Run explicitly with artifact and NEW state directories. No bootstrap or signed
URL is retained. Resume VM cleanup through gpu_release/supervisor.py if needed;
transfer.json retains the exact private bucket and object for recovery.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'gpu_release'))
from supervisor import Client, Supervisor
from observer import atomic_json

REGION = 'us-east-1'
ACCOUNT = '090208085542'
VPC = 'vpc-0c8ff9e3276495a4c'
UPLOAD_TIMEOUT = 90


class ApiError(RuntimeError):
    pass


def aws(service, operation, params):
    params = dict(params)
    extra = ['--body', params.pop('Body')] if operation == 'put-object' else []
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as request:
        json.dump(params, request)
        request.flush()
        try:
            result = subprocess.run(
                ['aws', service, operation, '--region', REGION, '--output', 'json',
                 '--cli-input-json', 'file://' + request.name] + extra,
                capture_output=True, text=True, timeout=UPLOAD_TIMEOUT if operation == 'put-object' else 90,
                env=dict(os.environ, AWS_PAGER='', AWS_MAX_ATTEMPTS='3'))
        except subprocess.TimeoutExpired:
            raise ApiError(operation + ':timeout') from None
    if result.returncode:
        match = re.search(r'An error occurred \(([A-Za-z0-9.]+)\)', result.stderr)
        raise ApiError(operation + ':' + (match.group(1) if match else 'transport_error'))
    return json.loads(result.stdout) if result.stdout.strip() else {}


def bootstrap(url, digest):
    # curl URL is never echoed; failures report only their numeric exit status.
    # The transfer object contains public artifacts, never workload credentials.
    if not re.fullmatch('[a-f0-9]{64}', digest) or "'" in url or '\n' in url:
        raise ValueError('bootstrap_input')
    return f'''#!/bin/bash
set -eu
shutdown -h +20 >/dev/null 2>&1
mkdir -p /work /proof
finish() {{
  code=$?
  if [ "$code" -ne 0 ]; then
    python3 - "$code" <<'PY' >/dev/console
import base64,hashlib,json,sys,zlib
raw=json.dumps({{'kind':'qb-decoder-isolated-cpu-vm','bootstrap_exit_code':int(sys.argv[1])}},sort_keys=True).encode()
data=base64.b64encode(zlib.compress(raw)).decode()
print('QB_ADAPTER_CHUNK',hashlib.sha256(raw).hexdigest(),0,1,data,flush=True)
PY
  fi
}}
trap finish EXIT
timeout 120 curl -fsSL '{url}' -o /proof/cpu.tar.gz
echo '{digest}  /proof/cpu.tar.gz' | sha256sum --check --status
tar --no-same-owner -xzf /proof/cpu.tar.gz -C /work
chmod -R a+rX /work
timeout 540 sh /work/install-toolchain.sh >/proof/toolchain.log 2>&1
python3 /work/guest.py >/dev/console 2>/proof/guest.stderr
'''.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    archive = args.artifact / 'cpu.tar.gz'
    identity = json.loads((args.artifact / 'archive.json').read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != identity['sha256']:
        raise ValueError('archive_identity')
    if aws('sts', 'get-caller-identity', {})['Account'] != ACCOUNT:
        raise ValueError('account_mismatch')
    args.directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    run = 'qb-proof-' + uuid.uuid4().hex
    bucket = run + '-cpu'
    state = {'run': run, 'account': ACCOUNT, 'region': REGION,
             'bucket': bucket, 'key': 'cpu.tar.gz', 'artifact': identity,
             'bucket_attempted': False, 'group_attempted': False}
    path = args.directory / 'transfer.json'
    def save():
        atomic_json(path, state)
    save()
    supervisor = None
    try:
        state['bucket_attempted'] = True
        save()
        aws('s3api', 'create-bucket', {'Bucket': bucket})
        aws('s3api', 'put-public-access-block', {'Bucket': bucket,
            'ExpectedBucketOwner': ACCOUNT, 'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                'BlockPublicPolicy': True, 'RestrictPublicBuckets': True}})
        aws('s3api', 'put-bucket-tagging', {'Bucket': bucket,
            'ExpectedBucketOwner': ACCOUNT,
            'Tagging': {'TagSet': [{'Key': 'QBProofRun', 'Value': run}]}})
        aws('s3api', 'put-object', {'Bucket': bucket, 'Key': state['key'],
            'Body': str(archive.resolve()), 'ExpectedBucketOwner': ACCOUNT,
            'ServerSideEncryption': 'AES256'})
        signed = subprocess.run(['aws', 's3', 'presign', 's3://' + bucket + '/' + state['key'],
            '--region', REGION, '--expires-in', '1800'], capture_output=True, text=True, timeout=60)
        if signed.returncode:
            raise ApiError('presign_failed')
        userdata = bootstrap(signed.stdout.strip(), identity['sha256'])
        del signed
        state['group_attempted'] = True
        save()
        group = aws('ec2', 'create-security-group', {'GroupName': run,
            'Description': 'Temporary isolated QB CPU qualification; no inbound',
            'VpcId': VPC, 'TagSpecifications': [{'ResourceType': 'security-group',
                'Tags': [{'Key': 'QBProofRun', 'Value': run}]}]})['GroupId']
        state['group'] = group
        save()
        plan = {'account': ACCOUNT, 'region': REGION, 'run': run,
            'image': 'ami-05a3e9423ae4d7a19', 'subnet': 'subnet-01fb5ff873d16c141',
            'group': group, 'vpc': VPC, 'instance_type': 'm7i.large', 'root_gib': 20}
        Supervisor.initialize(args.directory / 'vm', plan, userdata,
                              seconds=1200, cleanup_seconds=300)
        supervisor = Supervisor(args.directory / 'vm', Client(REGION))
        print('Launching one bounded CPU VM: ' + run, flush=True)
        supervisor.launch(userdata)
        del userdata
        print('VM launched; observing bounded console results.', flush=True)
        supervisor.observe()
        print('Checksummed result recovered; cleaning VM resources.', flush=True)
    except Exception as error:
        state['error'] = type(error).__name__ + ':' + str(error)
        save()
        print('Experiment stopped: ' + state['error'], flush=True)
    finally:
        errors = []
        if supervisor is not None:
            try:
                supervisor.cleanup()
                state['vm_cleanup_verified'] = True
            except Exception as error:
                errors.append('vm:' + type(error).__name__ + ':' + str(error))
        elif state['group_attempted']:
            try:
                groups = aws('ec2', 'describe-security-groups', {'Filters': [
                    {'Name': 'group-name', 'Values': [run]}, {'Name': 'vpc-id', 'Values': [VPC]},
                    {'Name': 'tag:QBProofRun', 'Values': [run]}]})['SecurityGroups']
                for group in groups:
                    aws('ec2', 'delete-security-group', {'GroupId': group['GroupId']})
                state['unlaunched_group_cleanup'] = True
            except Exception as error:
                errors.append('group:' + type(error).__name__ + ':' + str(error))
        if state['bucket_attempted']:
            try:
                try:
                    aws('s3api', 'head-bucket', {'Bucket': bucket, 'ExpectedBucketOwner': ACCOUNT})
                except ApiError as error:
                    if str(error) != 'head-bucket:404':
                        raise
                else:
                    aws('s3api', 'delete-object', {'Bucket': bucket, 'Key': state['key'],
                        'ExpectedBucketOwner': ACCOUNT})
                    aws('s3api', 'delete-bucket', {'Bucket': bucket, 'ExpectedBucketOwner': ACCOUNT})
                try:
                    aws('s3api', 'head-bucket', {'Bucket': bucket, 'ExpectedBucketOwner': ACCOUNT})
                except ApiError as error:
                    if str(error) != 'head-bucket:404':
                        raise
                else:
                    raise RuntimeError('bucket_still_present')
                state['transfer_cleanup_verified'] = True
            except Exception as error:
                errors.append('transfer:' + type(error).__name__ + ':' + str(error))
        state['cleanup_errors'] = errors
        save()
        print(json.dumps({key: state.get(key) for key in (
            'vm_cleanup_verified', 'transfer_cleanup_verified', 'cleanup_errors', 'error')}), flush=True)
    return 1 if state.get('error') or state['cleanup_errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
