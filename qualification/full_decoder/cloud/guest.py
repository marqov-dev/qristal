"""Fixed isolated-VM build and test stages; no workload credentials or network."""
import base64, hashlib, json, os, pathlib, shutil, sys, zlib
from capture_process import capture
OUT=pathlib.Path('/proof/out')
OUT.mkdir(parents=True, exist_ok=True)
shutil.chown(OUT, user='ubuntu', group='ubuntu')
report={'kind':'qb-decoder-isolated-cpu-vm','stages':[], 'source_manifest':json.loads(pathlib.Path('/work/manifest.json').read_text())}
INC=['-I/work/install-xacc/include/xacc','-I/work/install-xacc/include/quantum/gate','-I/work/install-xacc/include','-I/work/install-xacc/include/cppmicroservices4','-I/work/qristal-core/include','-I/work/qristal-decoder/include']
LIB=['-L/work/install-xacc/lib','-Wl,-rpath,/work/install-xacc/lib','-lxacc','-lxacc-quantum-gate','-lCppMicroServices','-ldl','-lpthread']
BASE=['c++','-std=c++20','-O1','-DNDEBUG']

def stage(name, command, seconds=180):
    # Unprivileged compilation/execution in a fresh network namespace. The VM
    # contains no instance credentials; only /proof/out is writable to ubuntu.
    prefix=['prlimit','--as=4294967296','--cpu=180','--nproc=256','--core=0','--',
            'unshare','--net','--','runuser','-u','ubuntu','--','env','-i',
            'PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2']
    item={'name':name,'command':command,'timeout_seconds':seconds}
    try:
        code,stdout,stderr=capture(prefix+command,timeout=seconds,stdout_limit=65536,stderr_limit=16384,retain_on_error=True)
        item.update(exit_code=code, stdout=stdout.decode(errors='replace')[-9000:], stderr=stderr.decode(errors='replace')[-3000:])
        (OUT/(name+'.stdout')).write_bytes(stdout)
        (OUT/(name+'.stderr')).write_bytes(stderr)
    except Exception as error:
        item['error']=type(error).__name__+':'+str(error)
        item['partial_stdout']=getattr(error,'stdout',b'').decode(errors='replace')[-9000:]
        item['partial_stderr']=getattr(error,'stderr',b'').decode(errors='replace')[-3000:]
    report['stages'].append(item)
    if item.get('exit_code') != 0: raise RuntimeError('stage_failed:'+name)
    return item

try:
    # Diagnostic subset: use unchanged public XACC implementations, with a
    # distinct provider identity. No claim of a rebuilt full generators bundle.
    stage('qft-provider-build',BASE+['-fPIC','-shared','-DUS_BUNDLE_NAME=marqov_qft_qualification',
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
    stage('core-plugin-build',BASE+['-fPIC','-shared','-DUS_BUNDLE_NAME=algorithm_es_plugin_bundle',
        '/work/qristal-core/src/algorithms/exponential_search/exponential_search.cpp',
        '/work/qristal-core/src/algorithms/exponential_search/exponential_search_algo_activator.cpp',
        '/work/build-core/algorithm_es/cppmicroservices_resources.cpp',
        '/work/build-core/algorithm_es/cppmicroservices_init.cpp']+INC+LIB+['-o','/proof/out/libalgorithm_es.so.1.8.1'])
    new=OUT/'libalgorithm_es.so.1.8.1'
    # CMake's build.make performs this POST_BUILD step after linking. The
    # generated cppmicroservices_resources.cpp is only a linker placeholder.
    stage('core-plugin-bundle',['/work/install-xacc/bin/usResourceCompiler4',
        '-b',str(new),'-z','/work/build-core/algorithm_es/res_0.zip'],30)
    for destination in ['/work/install-xacc/plugins/libalgorithm_es.so.1.8.1','/work/install-core/lib/libalgorithm_es.so.1.8.1']:
        shutil.copyfile(new,destination)
    report['core_plugin_sha256']=hashlib.sha256(new.read_bytes()).hexdigest()
    stage('input-test-build',BASE+['/work/qristal-decoder/src/quantum_decoder.cpp','/work/qristal-decoder/tests/FullDecoderInputValidation.cpp']+INC+
        ['-I/work/gtest/include','/work/build-core/lib/libgtest_main.a','/work/build-core/lib/libgtest.a']+LIB+['-o','/proof/out/input-tests'])
    result=stage('input-tests',['/proof/out/input-tests','--gtest_filter=FullDecoderInputValidation.*'],60)
    if '[  PASSED  ] 6 tests.' not in result['stdout']: raise RuntimeError('required_tests_not_passed')
    stage('tiny-build',BASE+['/work/qristal-decoder/src/quantum_decoder.cpp','/work/qualification/full_decoder/tiny_result_smoke.cpp']+INC+LIB+['-o','/proof/out/tiny-smoke'])
    tiny=stage('tiny-result',['/proof/out/tiny-smoke'],60)
    loaded=[line.removeprefix('LOADED_CORE_LIBRARY: ') for line in tiny['stdout'].splitlines()
            if line.startswith('LOADED_CORE_LIBRARY: ')]
    if len(loaded)!=1 or loaded[0] not in ('/work/install-xacc/plugins/libalgorithm_es.so.1.8.1',
                                         '/work/install-core/lib/libalgorithm_es.so.1.8.1'):
        raise RuntimeError('loaded_core_path_not_qualified')
    if hashlib.sha256(pathlib.Path(loaded[0]).read_bytes()).hexdigest()!=report['core_plugin_sha256']:
        raise RuntimeError('loaded_core_identity_mismatch')
except Exception as error:
    report['error']=type(error).__name__+':'+str(error)
finally:
    report['loaded_core_libraries']={}
    for item in report['stages']:
        for line in item.get('stdout','').splitlines():
            if line.startswith('LOADED_CORE_LIBRARY: '):
                path=pathlib.Path(line.removeprefix('LOADED_CORE_LIBRARY: '))
                if str(path) in ('/work/install-xacc/plugins/libalgorithm_es.so.1.8.1',
                                  '/work/install-core/lib/libalgorithm_es.so.1.8.1'):
                    report['loaded_core_libraries'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.suffix not in ('.stdout','.stderr','.json','.zip')}
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    if len(raw)>120000: raise RuntimeError('report_bounds')
    data=base64.b64encode(zlib.compress(raw)).decode(); digest=hashlib.sha256(raw).hexdigest()
    parts=[data[i:i+160] for i in range(0,len(data),160)]
    if len(parts)>128: raise RuntimeError('chunk_bounds')
    for repeat in range(2):
        for index,part in enumerate(parts):
            print(f'QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}',flush=True)
