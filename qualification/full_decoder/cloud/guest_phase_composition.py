"""One bounded controlled inverse prototype qualification; installed libraries unchanged."""
import base64, hashlib, json, pathlib, shutil, zlib
from capture_process import capture
from instrument_preparation import instrument
OUT=pathlib.Path('/proof/out')
OUT.mkdir(parents=True,exist_ok=True)
shutil.chown(OUT,user='ubuntu',group='ubuntu')
report={'kind':'qb-phase-composition-isolated-cpu-vm','stages':[],
        'source_manifest':json.loads(pathlib.Path('/work/manifest.json').read_text())}
INC=['-I/work/install-xacc/include/xacc','-I/work/install-xacc/include/quantum/gate',
     '-I/work/install-xacc/include','-I/work/install-xacc/include/cppmicroservices4','-I/work/qristal-core/include','-I/work/qristal-decoder/include','-I/work']
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
    stage('qft-provider-build',['c++','-std=c++20','-O1','-DNDEBUG']+['-fPIC','-shared','-DUS_BUNDLE_NAME=marqov_qft_qualification',
        '/work/xacc-qft/QFT.cpp','/work/xacc-qft/InverseQFT.cpp','/work/qft_activator.cpp',
        '/work/build-core/algorithm_es/cppmicroservices_resources.cpp',
        '/work/build-core/algorithm_es/cppmicroservices_init.cpp','-I/work/xacc-qft']+INC+LIB+
        ['-o','/proof/out/libmarqov_qft_qualification.so'])
    # Resource compiler uses a relative manifest entry so it is found by the bundle.
    shutil.copyfile('/work/qft-manifest.json',OUT/'manifest.json')
    stage('qft-provider-resources',['/bin/sh','-c',
        'cd /proof/out && /work/install-xacc/bin/usResourceCompiler4 -o qft.zip -n marqov_qft_qualification -r manifest.json'],30)
    stage('qft-provider-bundle',['/work/install-xacc/bin/usResourceCompiler4',
        '-b','/proof/out/libmarqov_qft_qualification.so','-z','/proof/out/qft.zip'],30)
    shutil.copyfile(OUT/'libmarqov_qft_qualification.so','/work/install-xacc/plugins/libmarqov_qft_qualification.so')
    stage('composition-build',['c++','-std=c++20','-O1','-DNDEBUG','/work/phase_composition_checks.cpp']+INC+LIB+['-o','/proof/out/composition-checks'])
    result=stage('composition-checks',['/proof/out/composition-checks'],60,60000)
    if 'PASS: 4 candidate interference checks; 4 legacy composition observations' not in result['stdout']:
        raise RuntimeError('missing_composition_marker')

    raw=pathlib.Path('/work/qristal-decoder/src/quantum_decoder.cpp').read_bytes()
    derived=instrument(raw);(OUT/'quantum_decoder.inventory.cpp').write_bytes(derived)
    report['inventory_source_identity']={'original_sha256':hashlib.sha256(raw).hexdigest(),'derived_sha256':hashlib.sha256(derived).hexdigest()}
    stage('inventory-build',['c++','-std=c++20','-O1','-DNDEBUG','/proof/out/quantum_decoder.inventory.cpp','/work/qualification/full_decoder/tiny_result_smoke.cpp']+INC+LIB+['-o','/proof/out/inventory-checks'])
    try:
        stage('inventory-checks',['/proof/out/inventory-checks'],60,30000)
    except RuntimeError:
        result=report['stages'][-1]
        if result.get('exit_code')!=1 or 'PREPARATION_INVENTORY_COMPLETE: construction only; no search or simulation' not in result.get('stdout','') or 'QB_INVENTORY_ONLY_STOP' not in result.get('stderr',''):
            raise
        report['inventory_intentional_stop']=True
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
