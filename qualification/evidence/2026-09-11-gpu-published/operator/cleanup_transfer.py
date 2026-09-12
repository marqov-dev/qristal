"""Remove only this experiment's exact temporary transfer resources."""
import datetime
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
bucket = 'codex-qb-release-proof-090208085542-20260911'
allowed = {'candidate.tar.gz', 'supervisor.tar.gz'}

def aws(*args):
    p = subprocess.run(['aws', 's3api', *args, '--region', 'us-east-1', '--output', 'json'], capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise SystemExit('transfer_cleanup_api_failed: ' + args[0])
    return json.loads(p.stdout or '{}')

uploads = aws('list-multipart-uploads', '--bucket', bucket).get('Uploads', [])
objects = aws('list-objects-v2', '--bucket', bucket).get('Contents', [])
if any(item['Key'] not in allowed for item in uploads + objects):
    raise SystemExit('unexpected_transfer_object')
for item in uploads:
    aws('abort-multipart-upload', '--bucket', bucket, '--key', item['Key'], '--upload-id', item['UploadId'])
for item in objects:
    aws('delete-object', '--bucket', bucket, '--key', item['Key'])
if aws('list-objects-v2', '--bucket', bucket).get('Contents') or aws('list-multipart-uploads', '--bucket', bucket).get('Uploads'):
    raise SystemExit('transfer_objects_remain')
aws('delete-bucket', '--bucket', bucket)
head = subprocess.run(['aws', 's3api', 'head-bucket', '--bucket', bucket, '--region', 'us-east-1'], capture_output=True, text=True, timeout=60)
if head.returncode == 0 or '(404)' not in head.stderr:
    raise SystemExit('bucket_absence_not_verified')
(root / 'transfer-cleanup.json').write_text(json.dumps({'bucket': bucket, 'bucket_absent': True, 'head_bucket_status': 404, 'deleted_objects': [i['Key'] for i in objects], 'aborted_multipart_uploads': len(uploads), 'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
print('TRANSFER_BUCKET_DELETED_AND_ABSENCE_VERIFIED')
