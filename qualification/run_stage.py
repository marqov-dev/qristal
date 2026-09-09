import pathlib,subprocess,uuid,os,sys,json,time
root=pathlib.Path(__file__).resolve().parents[2]
stage=sys.argv[1]
commands={
 'configure':['cmake','-S','/work/xacc','-B','/work/build-xacc','-DCMAKE_INSTALL_PREFIX=/work/install-xacc','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DMARQOV_CPU_PROBE=ON','-DXACC_BUILD_TESTS=OFF','-DXACC_BUILD_EXAMPLES=OFF','-DXACC_ENABLE_MPI=OFF','-DGIT_SUBMODULE=OFF','-DCMAKE_DISABLE_FIND_PACKAGE_Python=TRUE','-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=/work/googletest','-DBOOST_ARCHIVE_DIRECTORY=/work/archives','-DBOOST_DOWNLOAD_TO_BINARY_DIR=ON','-DCPR_USE_SYSTEM_CURL=ON','-DCMAKE_IGNORE_PREFIX_PATH=/opt/qb;/mnt/qb'],
 'build':['cmake','--build','/work/build-xacc','--parallel','2'],
 'test':['/work/build-xacc/marqov-acz-qpp'],
 'linkage':['ldd','/work/build-xacc/marqov-acz-qpp'],
 'install':['cmake','--install','/work/build-xacc'],
 'core-configure':['cmake','-S','/work/qristal-core','-B','/work/build-core','-DCMAKE_INSTALL_PREFIX=/work/install-core','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF','-DXACC_ROOT=/work/install-xacc','-DXACC_TAG=d1edaa7','-DXACC_REPOSITORY=https://github.com/eclipse-xacc/xacc.git','-DWITH_TNQVM=OFF','-DWITH_TKET=OFF','-DN_PROC=2','-DINSTALL_MISSING=ON','-DCPM_SOURCE_CACHE=/work/deps'],
 'noise-test':['python3','-B','/work/qristal/qualification/core_noise_smoke.py'],
 'core-test':['python3','-B','/work/qristal/qualification/core_cpu_smoke.py'],
 'python-lock':['python3','-m','pip','freeze','--all'],
 'core-plugins':['cmake','--build','/work/build-core','--parallel','2','--target','qb_gateset_transpiler','qb_qobj_compiler'],
 'core-build':['cmake','--build','/work/build-core','--parallel','2','--target','pycore'],

}
if stage not in commands:raise SystemExit('unknown stage')
if stage == 'test' and (root/'install-xacc/plugins/libxacc-qpp.so').exists():
 commands[stage].append('--installed')
if stage in ('core-test', 'noise-test'):
 modules=list((root/'build-core').glob('core.cpython-*.so'))
 if len(modules) != 1:raise SystemExit('Expected one rebuilt Core Python extension')
 package=root/'python/qristal';package.mkdir(parents=True,exist_ok=True)
 link=package/modules[0].name
 if not link.is_symlink():link.symlink_to(pathlib.Path('../../build-core')/modules[0].name)
 if link.resolve() != modules[0].resolve():raise SystemExit('Unexpected Core module link')
 for name in ('qb_gateset_transpiler', 'qb_qobj_compiler'):
  plugin=root/'build-core'/('lib'+name+'.so')
  if not plugin.exists():raise SystemExit('Build core-plugins before core-test')
  destination=root/'install-xacc/plugins'/plugin.name
  if not destination.is_symlink():destination.symlink_to(pathlib.Path('../../build-core')/plugin.name)
  if destination.resolve() != plugin.resolve():raise SystemExit('Unexpected Core plugin link')
(root/'home').mkdir(exist_ok=True)
name='marqov-qristal-cpu-'+uuid.uuid4().hex[:10]
image=json.loads((root/'toolchain.json').read_text())['image']
cmd=['docker','run','--rm','--name',name,'--platform','linux/amd64','--network',('bridge' if stage=='core-configure' else 'none'),'--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--read-only','--tmpfs','/tmp:rw,exec,size=256m','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck','--user',str(os.getuid())+':'+str(os.getgid()),'--mount','type=bind,source='+str(root)+',target=/work','--workdir','/work','--entrypoint','/usr/bin/env',image,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/work/home','GIT_CONFIG_NOSYSTEM=1','GIT_CONFIG_GLOBAL=/dev/null','GIT_TERMINAL_PROMPT=0','GIT_CONFIG_COUNT=3','GIT_CONFIG_KEY_0=safe.directory','GIT_CONFIG_VALUE_0=/work/deps/eigen3/3c806de9ccad1d4bcbbb741d21e21a08f67c8d04','GIT_CONFIG_KEY_1=safe.directory','GIT_CONFIG_VALUE_1=/work/deps/range-v3/c7042f84d5198c6c2266bf6a4eb359019dc83699','GIT_CONFIG_KEY_2=safe.directory','GIT_CONFIG_VALUE_2=/work/deps/args/ab85b487acb949e2b658105646501d1da3925112','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2','PYTHONPATH=/work/python','PIP_CONSTRAINT=/work/qristal/qualification/python-constraints.txt']+commands[stage]
start=time.time();status=None
try:
 with (root/(stage+'.log')).open('w') as f:
  p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=3600 if stage in ('build','core-configure','core-build','core-plugins') else 300)
  status=p.returncode
  if stage in ("test", "core-test", "noise-test"):
   output=(root/(stage+".log")).read_text()
   if "[error]" in output or "PASS:" not in output:status=1
 print(json.dumps({'stage':stage,'exit':status,'seconds':round(time.time()-start,1),'log':str(root/(stage+'.log'))}))
finally:
 subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
 (root/(stage+'-metadata.json')).write_text(json.dumps({'image':image,'command':commands[stage],'exit':status,'seconds':time.time()-start,'cpu':2,'memory_gib':4,'network':('bridge' if stage=='core-configure' else 'none'),'public_ubuntu_toolchain':True},indent=2))
sys.exit(status if status is not None else 1)
