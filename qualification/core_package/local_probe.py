"""Bounded local amd64-emulation smoke test; not hosted/native qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import uuid

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('qpp_bounded',HERE.parent/'runtime/bounded_process.py')
bounded=importlib.util.module_from_spec(spec);spec.loader.exec_module(bounded)


def absence(code,out,err,name):
    text=err.decode().strip().lower()
    return code==1 and not out.strip() and (('no such container: '+name) in text or ('no such object: '+name) in text)


def probe(image,output):
    if not re.fullmatch('sha256:[a-f0-9]{64}',image):raise ValueError('immutable local image ID required')
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    results=[]
    with tempfile.TemporaryDirectory(prefix='qpp-local-probe-') as d:
        inputs=Path(d);inputs.chmod(0o755)
        prefix='OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; '
        suffix='measure q[0] -> c[0]; measure q[1] -> c[1];'
        for name,gates in [('identity',''),('bell','h q[0]; cx q[0],q[1]; '),('q0','x q[0]; ')]:
            (inputs/(name+'.qasm')).write_text(prefix+gates+suffix)
            (inputs/(name+'.qasm')).chmod(0o644)
        base=['docker','run','--rm','--platform','linux/amd64','--network','none','--read-only',
              '--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL',
              '--security-opt','no-new-privileges','--user','65532:65532','--tmpfs','/tmp:rw,exec,size=512m',
              '--mount','type=bind,source='+str(inputs)+',target=/input,readonly']
        cases=[('capabilities',['--capabilities'])]
        for name in ('identity','bell','q0'):
            cases.append((name,['--qasm','/input/'+name+'.qasm','--shots','256']))
        cases.extend([('reject-aer',['--qasm','/input/bell.qasm','--backend','aer']),
                      ('reject-noise',['--qasm','/input/bell.qasm','--readout-p10','0.1'])])
        for label,args in cases:
            name='qpp-probe-'+uuid.uuid4().hex[:16]
            command=base+['--name',name,image]+args
            item={'case':label,'command':command,'passed':False}
            try:
                code,out,err=bounded.capture(command,timeout=60,stdout_limit=131072,stderr_limit=65536)
                item.update(exit_code=code,stdout=out.decode(),stderr=err.decode())
                if label.startswith('reject-'):
                    expected=b'qristal_sample_failed:'+ (b'backend' if label=='reject-aer' else b'noise_backend')+b'\n'
                    item['passed']=code==2 and out==b'' and err==expected
                else:
                    data=json.loads(out)
                    if label=='capabilities':
                        item['passed']=code==0 and data['backends']==['qpp'] and data['noise_cli']==[]
                    else:
                        counts=data['counts'];expected={'00','11'} if label=='bell' else ({'10'} if label=='q0' else {'00'})
                        item['passed']=(code==0 and data['backend']=='qpp' and data['shots']==256
                          and data['bit_order']=='qubit_0_first'
                          and data['program_sha256']==hashlib.sha256((inputs/(label+'.qasm')).read_bytes()).hexdigest()
                          and set(counts)==expected and all(type(v) is int and v>0 for v in counts.values())
                          and sum(counts.values())==256)
            except Exception as error:item['error']=type(error).__name__
            finally:
                # Exact task-owned container only; also handles timeout before --rm cleanup.
                try:
                    removed=bounded.capture(['docker','rm','-f',name],timeout=15,stdout_limit=1024,stderr_limit=2048)
                    code,out,err=bounded.capture(['docker','container','inspect','--format','{{.Id}}',name],
                                                timeout=15,stdout_limit=1024,stderr_limit=2048)
                    absent=absence(code,out,err,name)
                    item['cleanup']={'remove_exit_code':removed[0],'absence_verified':absent,
                                     'inspect_exit_code':code,'inspect_stdout':out.decode(),'inspect_stderr':err.decode()}
                    item['passed']=item['passed'] and absent
                except Exception as error:
                    item['cleanup']={'absence_verified':False,'error':type(error).__name__}
                    item['passed']=False
            results.append(item)
    result={'schema':'qb.qpp-local-emulation-probe/v1','image_id':image,'cases':results,
            'passed':all(r['passed'] for r in results),'native_amd64_hardware':False,
            'hosted':False,'redistribution_cleared':False}
    with output.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('output',type=Path)
    result=probe(**vars(p.parse_args()));print(json.dumps({'passed':result['passed'],'cases':len(result['cases'])}))
    if not result['passed']:raise SystemExit(1)
