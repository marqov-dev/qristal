"""Offline fixed-fixture harness, inside the qualified CPU container.

Expected facts are supplied by this test, not by any hosted admission service.
"""
import json
from pathlib import Path
import sys
import tempfile
from bounded_process import capture, ProcessError
from candidate import validate_candidate, CandidateError

passed=[]
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'program.qasm'
    for backend in ('qpp','aer'):
        for label,gates,expected in [('x0','x q[0];',{'10':17}),
                                     ('x1','x q[1];',{'01':17}),
                                     ('bell','h q[0]; cx q[0],q[1];',None)]:
            program=('OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; '+gates+' measure q -> c;').encode()
            path.write_bytes(program)
            options={'qubits':2,'shots':17 if expected else 4096,'seed':42}
            options_path=Path(directory)/'options.json'
            options_path.write_text(json.dumps(options))
            staged=json.loads(options_path.read_text())
            command=[sys.executable,'/opt/qristal/runtime.py','--qasm',str(path),'--backend',backend]
            for key,value in staged.items():command+=['--'+key,str(value)]
            code,out,err=capture(command,timeout=60)
            assert not err
            facts=dict(returncode=code,program=program,backend=backend,qubits=2,shots=options['shots'])
            result=validate_candidate(out,**facts)
            if expected:assert dict(result.counts)==expected,result
            else:
                assert set(dict(result.counts))=={'00','11'},result
                assert abs(dict(result.counts)['00']/4096-.5)<.04,result
            passed.append(backend+'-'+label)
            # Actual engine bytes must be rejected when expected immutable facts differ.
            for key,value in [('program',program+b' '),('backend','aer' if backend=='qpp' else 'qpp'),('shots',options['shots']+1)]:
                try:validate_candidate(out,**(facts | {key:value}))
                except CandidateError:passed.append(backend+'-'+label+'-reject-'+key)
                else:raise AssertionError('changed expected fact accepted')
    for label,source in [('zero-without-result','pass'),
                         ('killed','import os,signal; os.kill(os.getpid(),signal.SIGKILL)')]:
        code,out,err=capture([sys.executable,'-c',source])
        try:validate_candidate(out,**(facts | {'returncode':code}))
        except CandidateError:passed.append(label)
        else:raise AssertionError('missing result accepted')
    for label,source in [('oversize','import os; os.write(1,b"x"*200000)'),
                         ('stderr-overflow','import os; os.write(2,b"x"*10000)'),
                         ('deadline','import time; time.sleep(30)')]:
        try:capture([sys.executable,'-c',source],timeout=.5)
        except ProcessError as error:
            assert str(error)==('process_timeout' if label=='deadline' else 'process_output_limit')
            passed.append(label)
        else:raise AssertionError('process bound not enforced')
print(json.dumps({'passed':passed,'hosted_authority':False},indent=2))
