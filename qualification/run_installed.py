import pathlib, subprocess, uuid, os, sys, json, time
root=pathlib.Path(__file__).resolve().parents[2]
stage=sys.argv[1]
commands={
 'consumer-configure':['cmake','-S','/checks/consumer','-B','/probe/consumer','-Dqristal_core_DIR=/work/install-core'],
 'consumer-build':['cmake','--build','/probe/consumer','--parallel','2'],
 'consumer':['/probe/consumer/core-consumer'],
 'core':['python3','-s','-B','/checks/isolation.py','core_cpu_smoke.py'],
 'noise':['python3','-s','-B','/checks/isolation.py','core_noise_smoke.py'],
 'integration':['python3','-s','-B','/checks/isolation.py','integration_smoke.py'],
 'decoder-build':['c++','-std=c++17','-O1','-DNDEBUG','/checks/decoder_smoke.cpp','-I/work/install-xacc/include/xacc','-I/work/install-xacc/include/quantum/gate','-I/work/install-xacc/include','-I/work/install-xacc/include/cppmicroservices4','-L/work/install-xacc/lib','-Wl,-rpath,/work/install-xacc/lib','-lxacc','-lxacc-quantum-gate','-lCppMicroServices','-ldl','-lpthread','-o','/probe/decoder-smoke'],
 'decoder':['/probe/decoder-smoke'],
 'audit':['python3','-s','-B','/checks/audit.py'],
}
if stage not in commands:raise SystemExit('unknown stage')
(root/'runtime-probe').mkdir(exist_ok=True)
image=json.loads((root/'toolchain.json').read_text())['image']
name='marqov-installed-cpu-'+uuid.uuid4().hex[:10]
python_deps=root/('integration-deps' if stage=='integration' else 'home/.local/lib/python3.10/site-packages')
cmd=['docker','run','--rm','--name',name,'--platform','linux/amd64','--network','none','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--read-only','--tmpfs','/tmp:rw,exec,size=256m','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck','--user',str(os.getuid())+':'+str(os.getgid())]
mounts=[(root/'install-xacc','/work/install-xacc',True),(root/'install-core','/work/install-core',True),(python_deps,'/runtime/python-deps',True),(root/'installed-checks','/checks',True),(root/'install-integrations','/work/install-integrations',True),(root/'runtime-probe','/probe',False)]
for src,dst,readonly in mounts:cmd+=['--mount',f'type=bind,source={src},target={dst}'+(',readonly' if readonly else '')]
cmd+=['--workdir','/tmp','--entrypoint','/usr/bin/env',image,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2','PYTHONNOUSERSITE=1','PYTHONPATH=/work/install-core/lib:/runtime/python-deps:/work/install-integrations:/checks']+commands[stage]
start=time.time();status=None
try:
 with (root/('installed-'+stage+'.log')).open('w') as f:
  result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 status=result.returncode
 output=(root/('installed-'+stage+'.log')).read_text()
 if stage in ('core','noise','integration','decoder','audit') and ('PASS:' not in output or '[error]' in output):status=1
 print(json.dumps({'stage':stage,'exit':status,'seconds':round(time.time()-start,1),'log':str(root/('installed-'+stage+'.log'))}))
finally:
 subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
 (root/('installed-'+stage+'-metadata.json')).write_text(json.dumps({'image':image,'command':commands[stage],'exit':status,'seconds':time.time()-start,'cpu':2,'memory_gib':4,'network':'none','mounts':[{'source':str(s),'target':d,'readonly':ro} for s,d,ro in mounts],'environment':['empty environment','HOME=/tmp','PYTHONNOUSERSITE=1','PYTHONPATH=/work/install-core/lib:/runtime/python-deps:/work/install-integrations:/checks'],'ld_library_path':None},indent=2))
sys.exit(status if status is not None else 1)
