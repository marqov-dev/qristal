import hashlib,json,os,socket,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/qristal')
from program_guard import prepare
from local_pipeline import run_local

mode=Path('/inputs/mode').read_text().strip()
assert os.getuid()==65532
assert not Path('/qb-host-canary').exists()
assert not Path('/run/qb-management.sock').exists()
assert not any(k.startswith('AWS_') for k in os.environ)
assert set(p.name for p in Path('/sys/class/net').iterdir()) <= {'lo'}
for address in ('169.254.169.254','169.254.170.2'):
 s=socket.socket();s.settimeout(.2)
 try:
  s.connect((address,80))
 except OSError:pass
 else:raise AssertionError('metadata reachable')
 finally:s.close()
print('QB_ISOLATION='+json.dumps({'uid':os.getuid(),'interfaces':sorted(p.name for p in Path('/sys/class/net').iterdir()),'canary_absent':True,'management_socket_absent':True,'metadata_unreachable':True,'aws_environment_absent':True}),flush=True)
if mode=='killed':
 print('QB_WAITING',flush=True)
 time.sleep(300)
elif mode=='overflow':
 sys.stdout.write('X'*200000);sys.stdout.flush();time.sleep(300)
else:
 program=Path('/inputs/program.qasm').read_bytes();options=Path('/inputs/options.json').read_bytes()
 settings=json.loads(options)
 prepared=prepare(program,settings['qubits'])
 data={'original_sha256':prepared.original_sha256,'canonical_sha256':hashlib.sha256(prepared.canonical).hexdigest(),'options_sha256':hashlib.sha256(options).hexdigest(),'canonical':prepared.canonical.decode(),'logical_bits':['q[0]','q[1]']}
 if mode=='validate':
  expected=json.loads(Path('/inputs/preparation.json').read_text())
  assert data==expected
 if mode=='simulate':
  observed=run_local(program,options,backend='qpp')
  assert dict(observed.result.counts)=={'10':17}
  data['counts']=dict(observed.result.counts)
  assert observed.canonical_program_sha256==data['canonical_sha256']
 print('QB_RESULT='+json.dumps(data,sort_keys=True),flush=True)
