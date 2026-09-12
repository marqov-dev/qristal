#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/qb-recovery-probe.log /dev/console) 2>&1
shutdown -h +8
trap 'echo QB_GPU_HOST_FINISHED; shutdown -h now' EXIT
python3 - <<'PY'
import base64, hashlib, json, subprocess, time, zlib
started = time.time()
probe = subprocess.run(
    ['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],
    capture_output=True, text=True, timeout=30)
time.sleep(90)
result = {
    'schema': 'qb-supervisor-native-recovery-v1',
    'experiment': 'GPU host health and operator restart; no simulator execution',
    'gpu_probe_returncode': probe.returncode,
    'gpu': probe.stdout.strip() if probe.returncode == 0 else None,
    'started_epoch': started, 'finished_epoch': time.time(),
}
raw = json.dumps(result,sort_keys=True).encode()
digest = hashlib.sha256(raw).hexdigest()
encoded = base64.b64encode(zlib.compress(raw)).decode()
chunks = [encoded[i:i+160] for i in range(0,len(encoded),160)]
for _ in range(2):
    for i, chunk in enumerate(chunks):
        print('QB_ADAPTER_CHUNK', digest, i, len(chunks), chunk, flush=True)
PY
