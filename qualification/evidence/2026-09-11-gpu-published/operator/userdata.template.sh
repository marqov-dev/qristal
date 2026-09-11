#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/qb-gpu-proof.log /dev/console) 2>&1
shutdown -h +55
trap 'echo QB_GPU_HOST_FINISHED; shutdown -h now' EXIT
mkdir -p /opt/qb-proof
chmod 700 /opt/qb-proof
python3 - <<'PYBOOT'
import urllib.request, pathlib, hashlib, tarfile, json, time
root=pathlib.Path('/opt/qb-proof')
requests=__DOWNLOADS__
for item in requests:
    path=root/item['name']
    h=hashlib.sha256()
    end=time.monotonic()+1200
    try:
        with urllib.request.urlopen(item['url'],timeout=90) as response, path.open('wb') as out:
            while True:
                if time.monotonic()>end: raise TimeoutError()
                chunk=response.read(1024*1024)
                if not chunk: break
                out.write(chunk); h.update(chunk)
    except Exception as exc:
        print('QB_DOWNLOAD_FAILURE',item['name'],type(exc).__name__,flush=True)
        raise SystemExit(1)
    if 'sha256:'+h.hexdigest()!=item['sha256']: raise SystemExit('download_checksum')
    print('QB_DOWNLOAD_VERIFIED',item['name'],flush=True)
with tarfile.open(root/'supervisor.tar.gz') as archive:
    archive.extractall(root,filter='data')
PYBOOT
systemctl start docker
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
python3 -B /opt/qb-proof/qualification/gpu_release/import_image.py --archive /opt/qb-proof/candidate.tar.gz --archive-sha256 __ARCHIVE_SHA__ --bundle /opt/qb-proof/bundle --output /opt/qb-proof/build.json
python3 -B /opt/qb-proof/qualification/gpu_package/qualify.py --build /opt/qb-proof/build.json --output /var/tmp/qb-gpu-output
