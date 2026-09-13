"""Fixed isolated-VM build and test stages; no workload credentials or network."""
import base64, hashlib, json, os, pathlib, shutil, sys, zlib
from capture_process import capture
from patch_mcz import replace
from instrument_state import header, visitor
OUT=pathlib.Path('/proof/out')
OUT.mkdir(parents=True, exist_ok=True)
shutil.chown(OUT, user='ubuntu', group='ubuntu')
report={'kind':'qb-sparse-state-isolated-cpu-vm','stages':[], 'source_manifest':json.loads(pathlib.Path('/work/manifest.json').read_text())}
INC=['-I/work','-I/work/install-xacc/include/xacc','-I/work/install-xacc/include/quantum/gate','-I/work/install-xacc/include','-I/work/install-xacc/include/cppmicroservices4','-I/work/qristal-core/include','-I/work/qristal-decoder/include']
LIB=['-L/work/install-xacc/lib','-Wl,-rpath,/work/install-xacc/lib','-lxacc','-lxacc-quantum-gate','-lCppMicroServices','-ldl','-lpthread']
BASE=['c++','-std=c++20','-O1','-DNDEBUG']

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
    traced, patch, identity = replace(pathlib.Path('/work/qristal-core/src/algorithms/exponential_search/exponential_search.cpp').read_bytes(), pathlib.Path('/work/direct_mcz.hpp').read_bytes())
    report['mcz_probe_identity'] = identity
    (OUT/'exponential_search.traced.cpp').write_bytes(traced)
    (OUT/'mcz-probe.patch').write_text(patch)
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
        '/proof/out/exponential_search.traced.cpp',
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
    stage('tiny-build',BASE+['/work/qristal-decoder/src/quantum_decoder.cpp','/work/qualification/full_decoder/tiny_result_smoke.cpp']+INC+LIB+['-o','/proof/out/tiny-smoke'])
    header_path=pathlib.Path('/work/qristal-core/include/qristal/core/backends/sims/microsoft/sparse-sim/SparseSimulator.h')
    original_header=header_path.read_bytes()
    original_visitor=pathlib.Path('/work/SparseStateVecAccelerator.cpp').read_bytes()
    report['probe_identity']={'header_original':hashlib.sha256(original_header).hexdigest(),
                              'visitor_original':hashlib.sha256(original_visitor).hexdigest()}
    for mode in ('baseline','observed'):
        if mode=='observed':
            header_path.write_bytes(header(original_header))
            report['probe_identity']['header_derived']=hashlib.sha256(header_path.read_bytes()).hexdigest()
            stage('neutrality-build',BASE+['/work/state_neutrality.cpp']+INC+['-o','/proof/out/state-neutrality'])
            check=stage('neutrality-checks',['/proof/out/state-neutrality'],60)
            if 'STATE_NEUTRALITY ' not in check['stdout']:raise RuntimeError('neutrality_marker')
            source=visitor(original_visitor)
        else:source=original_visitor
        source_path=OUT/('sparse-'+mode+'.cpp');source_path.write_bytes(source)
        report['probe_identity']['visitor_'+mode]=hashlib.sha256(source).hexdigest()
        plugin=OUT/('libsparse-'+mode+'.so')
        stage(mode+'-sparse-build',BASE+['-fopenmp','-fPIC','-shared','-DUS_BUNDLE_NAME=sparse_simulator_plugin_bundle',
          str(source_path),'/work/build-core/sparse_simulator/cppmicroservices_resources.cpp',
          '/work/build-core/sparse_simulator/cppmicroservices_init.cpp']+INC+LIB+['-o',str(plugin)])
        stage(mode+'-sparse-bundle',['/work/install-xacc/bin/usResourceCompiler4','-b',str(plugin),'-z','/work/build-core/sparse_simulator/res_0.zip'],30)
        for destination in ['/work/install-core/lib/libsparse_simulator.so.1.8.1','/work/install-xacc/plugins/libsparse_simulator.so.1.8.1']:
            shutil.copyfile(plugin,destination)
        report['probe_identity'][mode+'_plugin']=hashlib.sha256(plugin.read_bytes()).hexdigest()
        try: stage(mode+'-tiny-result',['/proof/out/tiny-smoke'],60,25000)
        except RuntimeError:
            item=report['stages'][-1]
            if item.get('error')!='ProcessError:process_timeout':raise
        item=report['stages'][-1]
        output=item.get('stdout',item.get('partial_stdout',''))
        if 'LOADED_SPARSE_LIBRARY: /work/install-xacc/plugins/libsparse_simulator.so.1.8.1' not in output:
            raise RuntimeError('missing_loaded_sparse')
        item['loaded_sparse_sha256']=hashlib.sha256(pathlib.Path('/work/install-xacc/plugins/libsparse_simulator.so.1.8.1').read_bytes()).hexdigest()
except Exception as error:
    report['error']=type(error).__name__+':'+str(error)
finally:
    report['loaded_core_libraries']={}
    for item in report['stages']:
        for line in item.get('stdout',item.get('partial_stdout','')).splitlines():
            if line.startswith('LOADED_CORE_LIBRARY: '):
                path=pathlib.Path(line.removeprefix('LOADED_CORE_LIBRARY: '))
                if str(path) in ('/work/install-xacc/plugins/libalgorithm_es.so.1.8.1',
                                  '/work/install-core/lib/libalgorithm_es.so.1.8.1'):
                    report['loaded_core_libraries'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report['loaded_qft_libraries']={}
    for item in report['stages']:
        for line in item.get('stdout',item.get('partial_stdout','')).splitlines():
            if line=='LOADED_QFT_LIBRARY: /work/install-xacc/plugins/libmarqov_qft_qualification.so':
                path='/work/install-xacc/plugins/libmarqov_qft_qualification.so'
                report['loaded_qft_libraries'][path]=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    report['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.suffix not in ('.stdout','.stderr','.json','.zip')}
    for item in report['stages']:
        item.pop('command', None) # Exact commands remain in the source-bound guest.
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    data=base64.b64encode(zlib.compress(raw,9)).decode()
    if len(raw)>120000 or len(data)>128*160:
        # Retain a bounded failure report rather than losing every stage to a
        # bootstrap exit marker. This is diagnostic-only, never qualification.
        report={'kind':report['kind'],'error':'evidence_payload_bounds',
                'raw_bytes':len(raw),'encoded_bytes':len(data),
                'source_manifest':report['source_manifest'],
                'stages':[{'name':s['name'],'exit_code':s.get('exit_code'),
                           'error':s.get('error'),'stdout_bytes':len(s.get('stdout',s.get('partial_stdout','')))}
                          for s in report['stages']]}
        raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
        data=base64.b64encode(zlib.compress(raw,9)).decode()
    digest=hashlib.sha256(raw).hexdigest()
    parts=[data[i:i+160] for i in range(0,len(data),160)]
    if len(parts)>128: raise RuntimeError('minimal_report_bounds')
    for repeat in range(2):
        for index,part in enumerate(parts):
            print(f'QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}',flush=True)
