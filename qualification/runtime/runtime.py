"""Local workload CLI only. Not a hosted Marqov execution/authority protocol."""
import argparse, hashlib, json, os, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--capabilities',action='store_true')
    p.add_argument('--qasm',type=Path)
    p.add_argument('--backend',choices=['qpp','aer'],default='qpp')
    p.add_argument('--qubits',type=int,default=2)
    p.add_argument('--shots',type=int,default=4096)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--readout-p10',type=float,default=0)
    p.add_argument('--readout-p01',type=float,default=0)
    a=p.parse_args()
    if a.capabilities:
        print(Path('/opt/qristal/capabilities.json').read_text());return
    if not a.qasm or not 1<=a.qubits<=12 or not 1<=a.shots<=16384 or not 0<=a.seed<2**31:
        p.error('a QASM file and bounded qubits/shots/seed are required')
    if not all(0<=v<=1 for v in [a.readout_p10,a.readout_p01]):p.error('invalid noise probability')
    if (a.readout_p10 or a.readout_p01) and a.backend!='aer':p.error('readout noise requires aer')
    with a.qasm.open('rb') as f:data=f.read(65537)
    if len(data)>65536:p.error('QASM exceeds 64 KiB')
    source=data.decode('utf8')
    # This profile supports one explicitly sized register and the standard include only.
    import re
    if not re.match(r'\s*OPENQASM\s+2\.0\s*;',source):p.error('OpenQASM 2 required')
    if re.findall(r'\binclude\s+"([^"]+)"',source)!=['qelib1.inc']:p.error('only qelib1.inc is supported')
    regs=re.findall(r'\bqreg\s+\w+\s*\[\s*(\d+)\s*\]\s*;',source)
    if regs!=[str(a.qubits)]:p.error('one qreg matching --qubits is required')
    import qristal.core as q
    s=q.session();s.acc=a.backend;s.qn=a.qubits;s.sn=a.shots;s.seed=a.seed
    s.noplacement=True;s.nooptimise=True;s.aer_omp_threads=2
    s.remote_backend_database_path='/opt/qristal/empty-backends.yaml'
    s.instring=source
    if a.readout_p10 or a.readout_p01:
        nm=q.NoiseModel();nm.name='public_readout_demo'
        error=q.ReadoutError();error.p_10=a.readout_p10;error.p_01=a.readout_p01
        nm.set_qubit_readout_error(0,error);s.noise=True;s.noise_model=nm
    else:s.noise=False
    s.run();raw=s.results
    counts={''.join('1' if b else '0' for b in key):int(raw[key]) for key in raw}
    if sum(counts.values())!=a.shots:raise RuntimeError('unexpected shot total')
    print(json.dumps({'interface':'local-qristal-sample/experimental','program_sha256':hashlib.sha256(data).hexdigest(),'backend':a.backend,'shots':a.shots,'bit_order':'qubit_0_first','counts':counts},sort_keys=True))
if __name__=='__main__':main()
