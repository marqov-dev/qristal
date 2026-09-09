"""Create a local CPU image from qualified installs; never push or deploy it."""
import pathlib,subprocess,json,uuid,time,shutil,hashlib,tarfile
here=pathlib.Path(__file__).resolve().parent
root=here.parents[2]
base=json.loads((root/'toolchain.json').read_text())['base']
name='marqov-qristal-runtime-'+uuid.uuid4().hex[:10]
stage=root/'runtime-image-input';stage.mkdir(exist_ok=True)
licenses=stage/'licenses';licenses.mkdir(exist_ok=True)
shutil.copy2(here/'bell.qasm',root/'installed-checks/bell.qasm')
sources={}
for repo in ['qristal','qristal-core','qristal-decoder','qristal-integrations','xacc']:
 sources[repo]=subprocess.check_output(['git','-C',str(root/repo),'rev-parse','HEAD'],text=True).strip()
# Preserve license/notice texts from public C++ source inputs, including nested dependencies.
for top in ['qristal-core','qristal-decoder','qristal-integrations','xacc','deps']:
 for p in (root/top).rglob('*'):
  if not p.is_file() or p.is_symlink() or '.git' in p.parts:continue
  if p.name.upper().startswith(('LICENSE','COPYING','NOTICE','COPYRIGHT')):
   target=licenses/top/p.relative_to(root/top);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
boost_license=licenses/'boost-1.75.0';boost_license.mkdir(exist_ok=True)
with tarfile.open(root/'archives/boost_1_75_0.tar.bz2') as archive:
 (boost_license/'LICENSE_1_0.txt').write_bytes(archive.extractfile('boost_1_75_0/LICENSE_1_0.txt').read())
(stage/'sources.json').write_text(json.dumps(sources,indent=2))
script=stage/'install.sh'
script.write_text('''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
xargs apt-get install -y --no-install-recommends < /inputs/apt-runtime.txt
mkdir -p /work/install-core /work/install-xacc /work/install-integrations /runtime /opt/qristal /checks /probe
printf '{}\\n' > /opt/qristal/empty-backends.yaml
dpkg-query -W -f='${binary:Package}\\t${Version}\\n' > /runtime-packages.txt
apt-get clean
rm -rf /var/lib/apt/lists/*
''')
def call(args,**kw):return subprocess.run(args,check=True,timeout=1200,**kw)
start=time.time()
try:
 with (root/'runtime-image-build.log').open('w') as log:
  call(['docker','run','--name',name,'--platform','linux/amd64','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--security-opt','no-new-privileges','--mount',f'type=bind,source={here},target=/inputs,readonly','--mount',f'type=bind,source={script},target=/install.sh,readonly',base,'/bin/sh','/install.sh'],stdout=log,stderr=subprocess.STDOUT)
 # Copy only explicit qualified installations; no home, credentials, source/build tree or backend database.
 copies=[(root/'install-core/lib','/work/install-core/lib'),(root/'install-xacc/lib','/work/install-xacc/lib'),(root/'install-xacc/plugins','/work/install-xacc/plugins'),(root/'home/.local/lib/python3.10/site-packages','/runtime/python-core'),(root/'integration-deps','/runtime/python-integration'),(root/'install-integrations/.','/work/install-integrations/'),(root/'installed-checks/.','/checks/'),(root/'runtime-probe/decoder-smoke','/probe/decoder-smoke'),(here/'runtime.py','/opt/qristal/runtime.py'),(here/'capabilities.json','/opt/qristal/capabilities.json'),(licenses,'/opt/qristal/licenses'),(stage/'sources.json','/opt/qristal/sources.json')]
 for src,dst in copies:
  source=str(src)+('/.' if dst.endswith('/') and src.is_dir() else '')
  call(['docker','cp',source,name+':'+dst],stdout=subprocess.DEVNULL)
 changes=['USER 65532:65532','WORKDIR /tmp','ENV HOME=/tmp PYTHONNOUSERSITE=1 PYTHONPATH=/work/install-core/lib:/runtime/python-core:/work/install-integrations OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2','ENTRYPOINT ["python3", "/opt/qristal/runtime.py"]','CMD ["--capabilities"]','LABEL org.opencontainers.image.title="Qristal public CPU experimental runtime"']
 cmd=['docker','commit']
 for c in changes:cmd+=['--change',c]
 image=subprocess.check_output(cmd+[name],text=True).strip()
 call(['docker','cp',name+':/runtime-packages.txt',str(root/'runtime-packages.txt')],stdout=subprocess.DEVNULL)
 (root/'runtime-image.json').write_text(json.dumps({'image':image,'base':base,'sources':sources,'seconds':time.time()-start,'platform':'linux/amd64','published':False},indent=2))
 print(image)
finally:
 subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
