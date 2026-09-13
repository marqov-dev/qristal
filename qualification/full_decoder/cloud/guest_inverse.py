"""One bounded controlled inverse prototype qualification; installed libraries unchanged."""
import base64, hashlib, json, pathlib, shutil, zlib
from capture_process import capture
OUT=pathlib.Path('/proof/out')
OUT.mkdir(parents=True,exist_ok=True)
shutil.chown(OUT,user='ubuntu',group='ubuntu')
report={'kind':'qb-inverse-isolated-cpu-vm','stages':[],
        'source_manifest':json.loads(pathlib.Path('/work/manifest.json').read_text())}
INC=['-I/work/install-xacc/include/xacc','-I/work/install-xacc/include/quantum/gate',
     '-I/work/install-xacc/include','-I/work/install-xacc/include/cppmicroservices4','-I/work/qristal-core/include']
LIB=['-L/work/install-xacc/lib','-Wl,-rpath,/work/install-xacc/lib','-lxacc','-lxacc-quantum-gate','-lCppMicroServices','-ldl','-lpthread']
def stage(name, command, seconds=180, retained_stdout=9000):
    # Unprivileged compilation/execution in a fresh network namespace. The VM
    # contains no instance credentials; only /proof/out is writable to ubuntu.
    prefix=['prlimit','--as=4294967296','--cpu=180','--nproc=256','--core=0','--',
            'unshare','--net','--','runuser','-u','ubuntu','--','env','-i',
            'PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2']
    item={'name':name,'command':command,'timeout_seconds':seconds}
    try:
        code,stdout,stderr=capture(prefix+command,timeout=seconds,stdout_limit=65536,stderr_limit=16384,retain_on_error=True)
        item.update(exit_code=code, stdout=stdout.decode(errors='replace')[-retained_stdout:], stderr=stderr.decode(errors='replace')[-3000:])
        (OUT/(name+'.stdout')).write_bytes(stdout)
        (OUT/(name+'.stderr')).write_bytes(stderr)
    except Exception as error:
        item['error']=type(error).__name__+':'+str(error)
        item['partial_stdout']=getattr(error,'stdout',b'').decode(errors='replace')[-retained_stdout:]
        item['partial_stderr']=getattr(error,'stderr',b'').decode(errors='replace')[-3000:]
    report['stages'].append(item)
    if item.get('exit_code') != 0: raise RuntimeError('stage_failed:'+name)
    return item

try:
    stage('inverse-build',['c++','-std=c++20','-O1','-DNDEBUG','/work/inverse_checks.cpp']+INC+LIB+['-o','/proof/out/inverse-checks'])
    for mode,marker in [('negative','PASS: 12 inverse rejected inputs'),('qpp','PASS: 160 controlled inverse complex-state cases'),('sparse','PASS: 20 sparse controlled inverse roundtrips')]:
        result=stage('inverse-'+mode,['/proof/out/inverse-checks',mode],60,60000)
        if marker not in result['stdout']: raise RuntimeError('missing_pass_marker:'+mode)
except Exception as error:
    report['error']=type(error).__name__+':'+str(error)
finally:
    report['loaded_runtime_libraries']={}
    for item in report['stages']:
        for line in item.get('stdout',item.get('partial_stdout','')).splitlines():
            if line.startswith('LOADED_RUNTIME_LIBRARY: '):
                path=pathlib.Path(line.removeprefix('LOADED_RUNTIME_LIBRARY: '))
                if path.resolve().is_relative_to('/work') and path.is_file():
                    report['loaded_runtime_libraries'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.suffix not in ('.stdout','.stderr','.json')}
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    if len(raw)>120000: raise RuntimeError('report_bounds')
    data=base64.b64encode(zlib.compress(raw,9)).decode(); digest=hashlib.sha256(raw).hexdigest()
    parts=[data[i:i+160] for i in range(0,len(data),160)]
    if len(parts)>128: raise RuntimeError('chunk_bounds')
    for repeat in range(2):
        for index,part in enumerate(parts):
            print(f'QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}',flush=True)
