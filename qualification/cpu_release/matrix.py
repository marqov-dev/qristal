"""Distribution matrix; historical runtime harness remains unchanged."""
import pathlib,subprocess,json,uuid,time,argparse
here=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--image', help='Local immutable image ID to qualify')
parser.add_argument('--output', type=pathlib.Path, required=True)
args=parser.parse_args()
if not args.image or not __import__('re').fullmatch(r'sha256:[a-f0-9]{64}',args.image):parser.error('immutable image ID required')
image=args.image;root=args.output;root.mkdir(parents=True,exist_ok=False)
report=[]
def run(label,args,entry=None,env=None,expected=0,diagnostic=None):
 name='marqov-runtime-test-'+uuid.uuid4().hex[:10]
 cmd=['docker','run','--rm','--name',name,'--platform','linux/amd64','--network','none','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--read-only','--tmpfs','/tmp:rw,exec,size=128m','--cap-drop','ALL','--security-opt','no-new-privileges']
 if entry:cmd+=['--entrypoint',entry]
 if env:cmd+=['-e',env]
 start=time.time()
 try:
  p=subprocess.run(cmd+[image]+args,capture_output=True,text=True,timeout=180)
 finally:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
 (root/('image-'+label+'.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==expected,(label,p.returncode,p.stdout[-2000:],p.stderr[-2000:])
 if diagnostic is not None:assert not p.stdout and p.stderr.strip()==diagnostic,(label,p.stdout,p.stderr)
 report.append({'name':label,'exit':p.returncode,'seconds':time.time()-start,'command':cmd+[image]+args})
 return p.stdout
caps=json.loads(run('capabilities',['--capabilities']));assert caps['hosted_contract']=='not_integrated'
for label,fixture in [('core','core_cpu_smoke.py'),('noise','core_noise_smoke.py'),('integration','integration_smoke.py')]:
 env='PYTHONPATH=/work/install-core/lib:/runtime/python-integration:/work/install-integrations' if label=='integration' else None
 out=run(label,['-s','-B','/checks/isolation.py',fixture],entry='python3',env=env)
 assert 'PASS:' in out and 'ISOLATION_PASS:' in out and '[error]' not in out
assert run('decoder',[],entry='/probe/decoder-smoke').count('PASS:')==9
for label,extra in [('bell',[]),('noisy-bell',['--backend','aer','--readout-p10','.2','--readout-p01','.1'])]:
 result=json.loads(run(label,['--qasm','/checks/bell.qasm']+extra).splitlines()[-1]);counts=result['counts']
 assert sum(counts.values())==4096
 expected={'00':.5,'11':.5} if label=='bell' else {'00':.4,'10':.1,'11':.45,'01':.05}
 assert set(counts)==set(expected) and all(abs(counts[k]/4096-v)<.04 for k,v in expected.items()),result
run('reject-shots',['--qasm','/checks/bell.qasm','--shots','16385'],expected=2)
run('reject-gpu',['--qasm','/checks/bell.qasm','--backend','gpu'],expected=2,diagnostic='qristal_sample_failed:backend')
run('isolation',['-c',"import os,pathlib; assert os.getuid()==65532; assert not pathlib.Path('/work/build-core').exists(); assert not pathlib.Path('/usr/bin/c++').exists(); print('PASS: non-root, no build tree or compiler')"],entry='python3')
(root/'image-tests.json').write_text(json.dumps({'image':image,'tests':report,'no_host_mounts':True},indent=2))
print('PASS:',len(report),'image checks')
