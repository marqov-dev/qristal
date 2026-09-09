"""Run inside the bounded CPU container; validate the CLI as a subprocess."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

report=[]
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'input.qasm'
    def run(label, source, args=(), valid=True):
        path.write_bytes(source)
        p=subprocess.run(['python3','/opt/qristal/runtime.py','--qasm',str(path),*args],capture_output=True,timeout=60)
        assert len(p.stderr)<=128 and len(p.stdout)<=131073,(label,'output bounds',p.stderr[:128])
        if valid:
            assert p.returncode==0 and not p.stderr,(label,p.returncode,p.stderr)
            result=json.loads(p.stdout)
            assert p.stdout.count(b'\n')==1,(label,'extra output')
            assert result['program_sha256']==hashlib.sha256(source).hexdigest()
            assert sum(result['counts'].values())==result['shots']
            report.append(label)
            return result
        assert p.returncode!=0 and not p.stdout,(label,p.returncode,p.stdout,p.stderr)
        assert p.stderr.startswith(b'qristal_sample_failed:'),(label,p.stderr)
        report.append(label)
    for backend in ('qpp','aer'):
        for qubit in (0,1):
            source=f'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[{qubit}]; measure q -> c;'.encode()
            result=run(f'{backend}-x{qubit}',source,['--backend',backend,'--shots','17'])
            assert result['counts']=={('10' if qubit==0 else '01'):17},result
        for qubits,shots,seed in [(1,1,0),(12,16384,2147483647)]:
            source=f'OPENQASM 2.0; include "qelib1.inc"; qreg q[{qubits}]; creg c[{qubits}]; x q[0]; measure q -> c;'.encode()
            result=run(f'{backend}-bounds-{qubits}',source,['--backend',backend,'--qubits',str(qubits),'--shots',str(shots),'--seed',str(seed)])
            assert result['counts']=={'1'+'0'*(qubits-1):shots},result
    source=b'// unicode: \xc3\xa9\nOPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; measure q -> c;'
    run('comments',source)
    for label,args in [('noise-nan',['--readout-p10','nan']),('noise-qpp',['--readout-p01','.1']),('arguments',['--unknown','x'*10000]),('shots',['--shots','16385'])]:
        run(label,source,args,False)
    run('invalid-gate',source.replace(b'measure q -> c;',b'not_a_gate q[0]; measure q -> c;'),valid=False)
print(json.dumps({'passed':report},indent=2))
