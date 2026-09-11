"""Prepare bounded object downloads without printing signed URLs."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
acquisition = Path('/private/tmp/qb-published-candidate-20260911')
bucket = 'codex-qb-release-proof-090208085542-20260911'
transfer = json.loads((acquisition / 'transfer.json').read_text())
access = subprocess.run(['aws', 's3api', 'get-public-access-block', '--bucket', bucket, '--region', 'us-east-1'], capture_output=True, text=True, timeout=45)
if access.returncode:
    raise SystemExit('bucket_access_check_failed')
privacy = json.loads(access.stdout)['PublicAccessBlockConfiguration']
if set(privacy) != {'BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets'} or any(value is not True for value in privacy.values()):
    raise SystemExit('bucket_access_bounds')
items = []
heads = []
for name, size, digest in (
    ('candidate.tar.gz', transfer['archive_bytes'], transfer['archive_sha256']),
    ('supervisor.tar.gz', (root / 'supervisor.tar.gz').stat().st_size,
     'sha256:' + hashlib.sha256((root / 'supervisor.tar.gz').read_bytes()).hexdigest()),
):
    head = subprocess.run(['aws', 's3api', 'head-object', '--bucket', bucket, '--key', name, '--region', 'us-east-1'], capture_output=True, text=True, timeout=45)
    if head.returncode:
        raise SystemExit('object_not_available: ' + name)
    value = json.loads(head.stdout)
    if value['ContentLength'] != size or value['ServerSideEncryption'] != 'AES256':
        raise SystemExit('object_metadata_mismatch: ' + name)
    presign = subprocess.run(['aws', 's3', 'presign', 's3://' + bucket + '/' + name, '--expires-in', '3600', '--region', 'us-east-1'], capture_output=True, text=True, timeout=45)
    if presign.returncode:
        raise SystemExit('object_authorization_failed: ' + name)
    items.append({'name': name, 'url': presign.stdout.strip(), 'sha256': digest})
    heads.append({'key': name, 'bytes': size, 'sha256': digest, 'encryption': value['ServerSideEncryption']})
rendered = (root / 'userdata.template.sh').read_text().replace('__DOWNLOADS__', json.dumps(items)).replace('__ARCHIVE_SHA__', transfer['archive_sha256'])
if len(rendered.encode()) > 16384:
    raise SystemExit('userdata_size_bound')
path = root / 'userdata.sh'
path.touch(mode=0o600)
path.chmod(0o600)
path.write_text(rendered)
check = subprocess.run(['bash', '-n', str(path)], capture_output=True)
if check.returncode:
    raise SystemExit('userdata_syntax')
(root / 'transport-observed.json').write_text(json.dumps({'bucket': bucket, 'region': 'us-east-1', 'objects': heads, 'public_access_block': privacy, 'get_url_ttl_seconds': 3600, 'prepared_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
print('PRIVATE_OBJECTS_VERIFIED_AND_BOOTSTRAP_PREPARED')
