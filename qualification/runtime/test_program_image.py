import hashlib
import json
from pathlib import Path
import sys
import tempfile
from program_guard import prepare
from bounded_process import capture
from candidate import validate_candidate

passed=[]
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'canonical.qasm'
    for backend in ('qpp','aer'):
        for label,gates,expected in [('x0','x r[0];',{'10':257}),
                                     ('x1','x r[1];',{'01':257}),
                                     ('cx-forward','x r[0]; cx r[0],r[1];',{'11':257}),
                                     ('cx-reverse','x r[0]; cx r[1],r[0];',{'10':257}),
                                     ('bell','h r[0]; cx r[0],r[1];',None)]:
            original=('OPENQASM 2.0; include "qelib1.inc"; qreg r[2]; creg b[2]; '+gates+' measure r -> b;').encode()
            prepared=prepare(original,2)
            assert prepared.original_sha256==hashlib.sha256(original).hexdigest()
            path.write_bytes(prepared.canonical)
            code,out,err=capture([sys.executable,'/opt/qristal/runtime.py','--qasm',str(path),'--backend',backend,'--shots','257'])
            assert not err
            result=validate_candidate(out,returncode=code,program=prepared.canonical,backend=backend,qubits=2,shots=257)
            if expected:assert dict(result.counts)==expected,result
            else:
                counts=dict(result.counts)
                assert set(counts)=={'00','11'} and abs(counts['00']/257-.5)<.12,result
            passed.append(backend+'-'+label)
print(json.dumps({'passed':passed,'hosted_authority':False},indent=2))
