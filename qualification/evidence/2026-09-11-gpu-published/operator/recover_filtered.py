"""Retain only the qualification chunk protocol and allowlisted status markers."""
import json
from pathlib import Path
import re
import subprocess
import sys
root=Path(__file__).resolve().parent
sys.path.insert(0,'/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_package')
from console import recover, native
p=subprocess.run(['aws','ec2','get-console-output','--instance-id','i-0df84e33cffc898ce','--latest','--region','us-east-1','--output','json','--cli-connect-timeout','10','--cli-read-timeout','15'],capture_output=True,text=True,timeout=45)
if p.returncode:
    print('CONSOLE_API_FAILED',p.returncode)
    raise SystemExit(1)
value=json.loads(p.stdout)
output=native.STAMP.sub('',value.get('Output',''))
chunks=[m.group(0) for m in native.CHUNK.finditer(output)]
markers=re.findall(r'QB_DOWNLOAD_VERIFIED (?:candidate|supervisor)\.tar\.gz|QB_RELEASE_IMPORT_VERIFIED sha256:[a-f0-9]{64}|QB_GPU_HOST_FINISHED',output)
filtered='\n'.join(chunks+markers)+'\n'
(root/'console-filtered.txt').write_text(filtered)
print(json.dumps({'chunk_count':len(chunks),'status_markers':markers,'api_fields':sorted(value)}))
try:
    report,complete,truncated=recover(filtered)
except ValueError:
    print('COMPLETE_RESULT_NOT_AVAILABLE')
else:
    (root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    (root/'console-observed.txt').write_text(filtered)
    (root/'console-chunks.txt').write_text(complete)
    (root/'console-recovery.json').write_text(json.dumps({'discarded_truncated_nonfinal_fragments':truncated,'retention':'allowlisted qualification protocol only; full console excluded'},indent=2)+'\n')
    print('COMPLETE_RESULT_RECOVERED')
