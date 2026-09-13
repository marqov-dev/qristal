"""Fixed source-build experiment with verified output retrieval before S3 cleanup.

Requires an already installed boto3 on the operator host. It is never installed
by this wrapper. Uses normal AWS credential resolution without printing secrets.
"""
import base64
import gzip
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from archive import MAX_BYTES, digest, verify


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sign_put(client, bucket, account):
    try:
        return client.generate_presigned_url('put_object', Params={
            'Bucket': bucket, 'Key': 'source-output.tar.gz',
            'ServerSideEncryption': 'AES256', 'ExpectedBucketOwner': account},
            ExpiresIn=3900, HttpMethod='PUT')
    except Exception:
        raise RuntimeError('output_presign_failed') from None


def wrap_bootstrap(original, put_url, account):
    if any(c in put_url for c in ('\n', '\r', '"', '\\')) or not put_url.startswith('https://'):
        raise ValueError('invalid signed URL')
    if not account.isdigit():
        raise ValueError('invalid owner')
    text = original.decode()
    anchor = 'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
    if text.count(anchor) != 1:
        raise ValueError('guest entrypoint changed')
    config = ('url = "' + put_url + '"\nheader = "x-amz-server-side-encryption: AES256"\n'
              'header = "x-amz-expected-bucket-owner: ' + account + '"\n')
    payload = 'mkdir -p /proof/artifact-wrapper\numask 077\n'
    for name, data in [('archive.py', (HERE / 'archive.py').read_bytes()),
                       ('guest.py', (HERE / 'guest.py').read_bytes())]:
        payload += "printf '%s' '" + base64.b64encode(gzip.compress(data, mtime=0)).decode() + "' | base64 -d | gzip -d > /proof/artifact-wrapper/" + name + '\n'
    payload += "printf '%s' '" + base64.b64encode(config.encode()).decode() + "' | base64 -d > /proof/output-put.conf\n"
    # Restore ordinary output directory defaults expected by the original guest.
    payload += 'umask 022\npython3 /proof/artifact-wrapper/guest.py >/dev/console 2>/proof/guest.stderr'
    result = text.replace(anchor, payload).encode()
    if len(result) > 16384:
        raise ValueError('EC2 userdata byte bound')
    return result


@contextmanager
def retention_deadline(deadline):
    """Main-thread Unix hard timer covers network calls, verification and fsync."""
    remaining = min(300, deadline - time.monotonic())
    if remaining < 1:
        raise TimeoutError('no retention budget')
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise RuntimeError('existing process timer')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise RuntimeError('retention deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def download(client, state, directory, recovered, *, deadline=None):
    identity = recovered.get('output_artifact')
    if not identity or recovered.get('output_artifact_error'):
        raise ValueError('output artifact unavailable')
    if not isinstance(identity.get('bytes'), int) or not 0 < identity['bytes'] <= MAX_BYTES:
        raise ValueError('output byte bound')
    deadline = min(time.monotonic() + 300, deadline if deadline is not None else float('inf'))
    if deadline <= time.monotonic():
        raise TimeoutError('download deadline')
    response = client.get_object(Bucket=state['bucket'], Key='source-output.tar.gz',
                                 ExpectedBucketOwner=state['account'])
    body = response['Body']
    try:
        if response['ContentLength'] != identity['bytes']:
            raise ValueError('object size mismatch')
        path = directory / 'output.tar.gz'
        total = 0
        with path.open('xb') as stream:
            for data in body.iter_chunks(chunk_size=1024 * 1024):
                if time.monotonic() > deadline:
                    raise ValueError('download time bound')
                total += len(data)
                if total > identity['bytes']:
                    raise ValueError('download byte bound')
                stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        body.close()
    original = {k: v for k, v in recovered.items() if k != 'output_artifact'}
    return verify(path, identity, original)


def main():
    source = load('artifact_source_runner', HERE.parent / 'source_build/run.py')
    lifecycle = source.lifecycle
    # Import is intentionally before any resource creation.
    import boto3
    from botocore.config import Config
    client = boto3.client('s3', region_name=lifecycle.REGION,
                          config=Config(connect_timeout=10, read_timeout=30,
                                        retries={'max_attempts': 2}, signature_version='s3v4'))
    original_aws = lifecycle.aws
    lifecycle.UPLOAD_TIMEOUT = 300
    lifecycle.SupervisorBase = lifecycle.Supervisor
    directory = Path(sys.argv[2]) if len(sys.argv) == 3 else None
    context = {}

    def aws(service, operation, params):
        if service == 's3api' and operation == 'create-bucket':
            lifecycle.atomic_json(directory / 'wrapper-identity.json', {
                'schema': 'qb.source-artifact-wrapper/v1',
                'output_key': 'source-output.tar.gz',
                'files': {name: digest((HERE / name).read_bytes()) for name in
                          ('run.py', 'guest.py', 'archive.py', 'verify.py', 'requirements-operator.txt')}})
        result = original_aws(service, operation, params)
        if service == 's3api' and operation == 'put-object':
            context['bucket'] = params['Bucket']
        return result

    def bootstrap(url, digest):
        return wrap_bootstrap(source.bootstrap(url, digest),
                              sign_put(client, context['bucket'], lifecycle.ACCOUNT), lifecycle.ACCOUNT)

    class Supervisor(source.SourceSupervisor):
        def observe(self, **kwargs):
            super().observe(**kwargs)
            transfer = json.loads((directory / 'transfer.json').read_text())
            report = json.loads((directory / 'vm/recovered.json').read_text())['result']
            retention = {'bucket': transfer['bucket'], 'key': 'source-output.tar.gz',
                         'account': transfer['account'], 'verified': False}
            lifecycle.atomic_json(directory / 'retention.json', retention)
            try:
                # No fresh budget: all retention work must finish before the
                # original observation deadline, reserving its cleanup window.
                deadline = self.deadline('observe_until')
                with retention_deadline(deadline):
                    checker = load('artifact_native_checker', HERE.parent / 'source_build/verify.py')
                    manifest = (Path(sys.argv[1]) / 'work/manifest.json').read_bytes()
                    retention['native'] = checker.verify(report, manifest)
                    if not retention['native']['native_passed']:
                        raise ValueError('native qualification failed')
                    retention.update(download(client, transfer, directory, report, deadline=deadline))
            except Exception as error:
                retention['error'] = type(error).__name__
                raise RuntimeError('output_retention_failed') from None
            finally:
                lifecycle.atomic_json(directory / 'retention.json', retention)

    # Delete the output only after observation has attempted durable retrieval.
    # If retrieval failed, preserve the private object and exact recovery identity.
    def cleanup_aws(service, operation, params):
        if service == 's3api' and operation == 'delete-bucket':
            retention_path = directory / 'retention.json'
            retention = json.loads(retention_path.read_text()) if retention_path.exists() else {}
            if not retention.get('verified'):
                # An upload may have succeeded even if the console report was lost.
                raise RuntimeError('output_bucket_retained_for_recovery')
            original_aws('s3api', 'delete-object', {'Bucket': params['Bucket'],
                'Key': 'source-output.tar.gz', 'ExpectedBucketOwner': lifecycle.ACCOUNT})
        return aws(service, operation, params)

    lifecycle.aws = cleanup_aws
    lifecycle.bootstrap = bootstrap
    lifecycle.Supervisor = Supervisor
    return lifecycle.main()


if __name__ == '__main__':
    sys.exit(main())
