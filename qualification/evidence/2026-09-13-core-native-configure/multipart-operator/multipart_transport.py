"""Optional exact-payload multipart transport; does not change the native bundle.

Run with the same PREPARED_ARTIFACT NEW_STATE arguments as run.py. The upload
child gets 3600 seconds total, two workers and 8 MiB parts. Failure triggers an
independent at-most-90-second abort child for the exact persisted upload ID.
No VM is launched by this module itself; unchanged run.py continues only after
verified completion. This module has not been exercised against AWS.

IAM: create/upload/complete use s3:PutObject; verification uses s3:GetObject;
failure cleanup additionally requires s3:AbortMultipartUpload and
s3:ListMultipartUploadParts to verify absence of that exact upload. No bucket
upload listing or broad deletion is attempted. If create succeeds but its response is lost, the
upload ID cannot be recovered here: the exact temporary bucket remains an
explicit operator recovery obligation. Never infer absence from missing state.

HEAD checks size, caller-supplied source-hash metadata and encryption, not an
independent whole-object SHA256. Integrity also uses checked part SHA256 values
and local pre/post hashing. The unchanged guest's full archive SHA256 check is
authoritative before execution. Multipart absence does not prove object absence
when a completion response was lost; never delete or relaunch on that inference.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SHA256 = 'c1b393fa0f5e33fd34764834704afb6e6f8151afe2ee5ac68df65bd20231b9b7'
BYTES = 314255079
PART_BYTES = 8 * 1024 * 1024
WORKERS = 2
ACCOUNT = '090208085542'
REGION = 'us-east-1'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, state):
    temporary = path.with_suffix('.new')
    with temporary.open('w') as stream:
        json.dump(state, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_payload(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != BYTES or file_hash(path) != SHA256:
        raise ValueError('unapproved multipart payload')


def upload(client, payload, state_path, state):
    """Injected client makes all offline tests independent of AWS and boto3."""
    validate_payload(payload)
    owner = {'Bucket': state['bucket'], 'ExpectedBucketOwner': ACCOUNT}
    state['create_attempted'] = True
    save(state_path, state)
    created = client.create_multipart_upload(**owner, Key=state['key'],
        ServerSideEncryption='AES256', ChecksumAlgorithm='SHA256', Metadata={'source-sha256': SHA256})
    state['upload_id'] = created['UploadId']
    state['phase'] = 'uploading'
    save(state_path, state)  # Durable ID before any part is scheduled.

    def part(number):
        import base64
        offset = (number - 1) * PART_BYTES
        with Path(payload).open('rb') as stream:
            stream.seek(offset)
            data = stream.read(min(PART_BYTES, BYTES - offset))
        if len(data) != min(PART_BYTES, BYTES - offset):
            raise ValueError('multipart input changed')
        checksum = base64.b64encode(hashlib.sha256(data).digest()).decode()
        response = client.upload_part(**owner, Key=state['key'], UploadId=state['upload_id'],
            PartNumber=number, Body=data, ChecksumSHA256=checksum)
        if response.get('ChecksumSHA256') != checksum:
            raise ValueError('part checksum mismatch')
        return {'PartNumber': number, 'ETag': response['ETag'], 'ChecksumSHA256': checksum}

    count = (BYTES + PART_BYTES - 1) // PART_BYTES
    parts = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(part, number) for number in range(1, count + 1)]
        try:
            for future in as_completed(futures):
                parts.append(future.result())
                state['parts_received'] = len(parts)
                save(state_path, state)
        except Exception:
            for future in futures:
                future.cancel()
            raise
    # Refuse to complete if the local approved file changed while parts were read.
    validate_payload(payload)
    parts.sort(key=lambda item: item['PartNumber'])
    state['phase'] = 'completing'
    save(state_path, state)
    client.complete_multipart_upload(**owner, Key=state['key'], UploadId=state['upload_id'],
                                    MultipartUpload={'Parts': parts})
    response = client.head_object(**owner, Key=state['key'])
    if (response.get('ContentLength') != BYTES or response.get('Metadata', {}).get('source-sha256') != SHA256
            or response.get('ServerSideEncryption') != 'AES256'):
        raise ValueError('completed object identity')
    state.update(phase='complete', verified=True, parts=count)
    save(state_path, state)


def abort(client, state_path):
    state = json.loads(state_path.read_text())
    if state.get('verified'):
        return
    if not state.get('upload_id'):
        state['abort_error'] = 'upload_identity_unresolved' if state.get('create_attempted') else 'create_not_attempted'
        save(state_path, state)
        return
    if state.get('phase') == 'completing':
        state['object_completion_uncertain'] = True
    try:
        try:
            client.abort_multipart_upload(Bucket=state['bucket'], Key=state['key'],
                UploadId=state['upload_id'], ExpectedBucketOwner=ACCOUNT)
            state['abort_requested'] = True
        except Exception as error:
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code != 'NoSuchUpload':
                raise RuntimeError('abort request failed') from None
            state['abort_already_absent_response'] = True
        # NoSuchUpload is the expected exact-upload absence response.
        try:
            client.list_parts(Bucket=state['bucket'], Key=state['key'],
                UploadId=state['upload_id'], ExpectedBucketOwner=ACCOUNT)
        except Exception as error:
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code != 'NoSuchUpload':
                raise RuntimeError('abort absence unverified') from None
        else:
            raise RuntimeError('upload still present')
        state['abort_verified'] = True
        state['multipart_absence_verified'] = True
    except Exception as error:
        state['abort_error'] = type(error).__name__
    save(state_path, state)


def client():
    import boto3
    from botocore.config import Config
    return boto3.client('s3', region_name=REGION, config=Config(connect_timeout=10,
        read_timeout=45, retries={'max_attempts': 1}, signature_version='s3v4'))


def child(action, payload, state_path):
    try:
        if action == 'upload':
            upload(client(), payload, state_path, json.loads(state_path.read_text()))
        else:
            abort(client(), state_path)
        return 0
    except Exception as error:
        state = json.loads(state_path.read_text())
        state['error'] = type(error).__name__  # No SDK error text or signed request data.
        save(state_path, state)
        return 1


def transfer(params, directory):
    if params.get('ExpectedBucketOwner') != ACCOUNT or params.get('ServerSideEncryption') != 'AES256' or params.get('Key') != 'cpu.tar.gz':
        raise ValueError('multipart scope')
    payload = Path(params['Body']).resolve()
    validate_payload(payload)
    state_path = directory / 'multipart-transport.json'
    if state_path.exists():
        raise ValueError('multipart state must be new')
    state = {'schema': 'qb.core-multipart-transport/v1', 'bucket': params['Bucket'], 'key': params['Key'],
        'account': ACCOUNT, 'region': REGION, 'payload_sha256': SHA256, 'payload_bytes': BYTES,
        'wrapper_sha256': file_hash(__file__), 'part_bytes': PART_BYTES, 'workers': WORKERS,
        'upload_seconds': 3600, 'abort_seconds': 90, 'phase': 'prepared', 'verified': False}
    save(state_path, state)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child']
    failed = False
    timed_out = False
    exit_code = None
    try:
        completed = subprocess.run(command + ['upload', str(payload), str(state_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3600)
        failed = completed.returncode != 0
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        failed = True
        timed_out = True
    state = json.loads(state_path.read_text())
    state.update(upload_process_timeout=timed_out, upload_process_exit=exit_code)
    save(state_path, state)
    if failed or not state.get('verified'):
        try:
            subprocess.run(command + ['abort', str(payload), str(state_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, check=True)
        except Exception as error:
            state = json.loads(state_path.read_text())
            state['abort_process_error'] = type(error).__name__
            save(state_path, state)
        raise RuntimeError('multipart_transport_failed; see exact recovery state')
    return {}


def main():
    if len(sys.argv) == 5 and sys.argv[1] == '--child':
        return child(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
    if len(sys.argv) != 3:
        raise SystemExit('usage: multipart_transport.py PREPARED_ARTIFACT NEW_STATE')
    directory = Path(sys.argv[2])
    spec = importlib.util.spec_from_file_location('unchanged_core_runner', HERE / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original_load = runner.load
    def load(name, path):
        module = original_load(name, path)
        if name == 'core_source_lifecycle':
            original_aws = module.lifecycle.aws
            def aws(service, operation, params):
                if service == 's3api' and operation == 'put-object':
                    return transfer(params, directory)
                return original_aws(service, operation, params)
            module.lifecycle.aws = aws
        return module
    runner.load = load
    return runner.main()


if __name__ == '__main__':
    sys.exit(main())
