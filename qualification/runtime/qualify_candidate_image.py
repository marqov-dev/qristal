"""Overlay local candidate-validation fixtures on an existing CPU image and test offline.

No native rebuild, registry push, network, host mount or platform change.
"""
import argparse
import json
from pathlib import Path
import subprocess
import uuid

here=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--parent',required=True,help='Qualified local CPU image ID')
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
name='qristal-candidate-'+uuid.uuid4().hex[:10]
def call(args,**kwargs):
    return subprocess.run(['docker',*args],check=True,timeout=240,**kwargs)
try:
    call(['create','--name',name,'--platform','linux/amd64',a.parent],stdout=subprocess.DEVNULL)
    for file in ['candidate.py','bounded_process.py','test_candidate.py','test_bounded_process.py','test_candidate_image.py']:
        call(['cp',str(here/file),name+':/opt/qristal/'+file])
    image=call(['commit',name],capture_output=True,text=True).stdout.strip()
finally:
    subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
(a.output/'image.json').write_text(json.dumps({'image':image,'parent':a.parent},indent=2)+'\n')
for test in ['test_candidate.py','test_bounded_process.py','test_candidate_image.py']:
    name='qristal-test-'+uuid.uuid4().hex[:10]
    args=['run','--rm','--name',name,'--platform','linux/amd64','--network','none','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--read-only','--tmpfs','/tmp:rw,exec,size=128m','--cap-drop','ALL','--security-opt','no-new-privileges','--entrypoint','python3',image,'-B','/opt/qristal/'+test]
    try:
        result=call(args,capture_output=True,text=True)
        (a.output/(test+'.log')).write_text(result.stdout+result.stderr)
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
print(image)
