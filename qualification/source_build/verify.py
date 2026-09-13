"""Classify a source-build report without treating recovery as native success."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

LIMITS = {'builder':600, 'inventory':60, 'configure':300, 'build':900,
          'build-test':60, 'install':120, 'consumer-build':120,
          'installed-linkage':60, 'installed-test':60}


def verify(report, manifest_bytes):
    if report.get('kind') != 'qb-xacc-fresh-source-v1':
        raise ValueError('report kind')
    if report.get('error') or report.get('bootstrap_exit_code'):
        if report.get('native_passed') is True:
            raise ValueError('conflicting success and failure')
        return {'native_passed': False, 'reason': report.get('error', 'bootstrap failure'),
                'completed_stages': list(report.get('stages', {}))}
    manifest = json.loads(manifest_bytes)
    if (manifest.get('schema') != 'qb.source-build-input/v1'
            or hashlib.sha256(manifest_bytes).hexdigest() != report.get('manifest_sha256')):
        raise ValueError('manifest binding')
    here = Path(__file__).resolve().parent
    if manifest.get('files', {}).get('guest.py', {}).get('sha256') != hashlib.sha256((here / 'guest.py').read_bytes()).hexdigest():
        raise ValueError('guest harness binding')
    summary = here.parent / 'evidence/2026-09-13-pristine-sources/summary.json'
    if manifest.get('source_summary_sha256') != hashlib.sha256(summary.read_bytes()).hexdigest():
        raise ValueError('source summary binding')
    summary_data = json.loads(summary.read_text())
    materials = {x['path']: x['sha256'] for x in summary_data['materials']}
    if manifest.get('transformations') != [
        {'patch': 'xacc-cpu.patch', 'sha256': materials['xacc-cpu.patch'], 'target': 'xacc'},
        {'patch': 'cppmicroservices.patch', 'sha256': materials['cppmicroservices.patch'], 'target': 'xacc/tpls/cppmicroservices'}]:
        raise ValueError('transformation identities')
    if report.get('native_passed') is not True or set(report.get('stages', {})) != set(LIMITS):
        raise ValueError('incomplete stage set')
    image = report.get('builder_image', '')
    if not re.fullmatch('sha256:[a-f0-9]{64}', image):
        raise ValueError('builder image identity')
    for name, limit in LIMITS.items():
        stage = report['stages'][name]
        seconds = stage.get('seconds')
        if (stage.get('exit') != 0 or stage.get('timeout') is not False or
                type(seconds) not in (int,float) or not math.isfinite(seconds) or
                not 0 <= seconds <= limit + 10 or
                not re.fullmatch('[a-f0-9]{64}', stage.get('log_sha256', ''))):
            raise ValueError('stage result: ' + name)
        command = stage.get('command', [])
        if name == 'builder':
            if command != ['docker','build','--iidfile','/proof/builder-id','/proof/toolchain']:
                raise ValueError('builder command')
            continue
        if stage.get('container_removed') is not True:
            raise ValueError('container cleanup: ' + name)
        prefix = ['docker','run','--name','qb-source-'+name,'--network','none','--read-only','--cpus','2',
                  '--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL',
                  '--security-opt','no-new-privileges','--user','65532:65532','--tmpfs','/tmp:rw,exec,size=512m',
                  '--workdir','/tmp']
        installed = name in ('consumer-build','installed-linkage','installed-test')
        paths = ['install-xacc'] if installed else ['xacc','googletest','archives','acz_qpp_smoke.cpp','build-xacc','install-xacc']
        for item in paths:
            writable = item in ('build-xacc','install-xacc') and not installed
            prefix += ['--mount','type=bind,source=/work/'+item+',target=/work/'+item+('' if writable else ',readonly')]
        if installed:
            prefix += ['--mount','type=bind,source=/proof/consumer,target=/consumer,readonly',
                       '--mount','type=bind,source=/proof/consumer-output,target=/consumer-output'+('' if name=='consumer-build' else ',readonly')]
        prefix += ['--entrypoint','/usr/bin/env',image,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2']
        if command[:len(prefix)] != prefix:
            raise ValueError('isolation command: ' + name)
        expected = {'build':['cmake','--build','/work/build-xacc','--parallel','2'],
                    'build-test':['/work/build-xacc/marqov-acz-qpp'],
                    'install':['cmake','--install','/work/build-xacc'],
                    'installed-linkage':['ldd','/consumer-output/acz'],
                    'installed-test':['/consumer-output/acz','--installed']}
        expected.update({'configure': ['cmake', '-S', '/work/xacc', '-B', '/work/build-xacc', '-DCMAKE_INSTALL_PREFIX=/work/install-xacc', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG', '-DMARQOV_CPU_PROBE=ON', '-DXACC_BUILD_TESTS=OFF', '-DINSTALL_GTEST=OFF', '-DXACC_BUILD_EXAMPLES=OFF', '-DXACC_ENABLE_MPI=OFF', '-DGIT_SUBMODULE=OFF', '-DCMAKE_DISABLE_FIND_PACKAGE_Python=TRUE', '-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=/work/googletest', '-DBOOST_ARCHIVE_DIRECTORY=/work/archives', '-DBOOST_DOWNLOAD_TO_BINARY_DIR=ON', '-DCPR_USE_SYSTEM_CURL=ON', '-DCMAKE_IGNORE_PREFIX_PATH=/opt/qb;/mnt/qb'], 'inventory': ['sh', '-c', 'c++ --version; cmake --version; python3 --version; cat /toolchain-packages.txt'], 'consumer-build': ['c++', '-std=c++17', '-O1', '-DNDEBUG', '/consumer/acz.cpp', '-I/work/install-xacc/include/xacc', '-I/work/install-xacc/include', '-I/work/install-xacc/include/cppmicroservices4', '-L/work/install-xacc/lib', '-Wl,-rpath,/work/install-xacc/lib', '-lxacc', '-lCppMicroServices', '-ldl', '-lpthread', '-o', '/consumer-output/acz']})
        if name in expected and command[len(prefix):] != expected[name]:
            raise ValueError('stage command: ' + name)
    test = report['stages']['installed-test']['tail']
    if 'PASS: ACZ registered' not in test or '[error]' in test:
        raise ValueError('installed test marker')
    linkage = report['stages']['installed-linkage']['tail']
    if len(linkage) >= 2200 or 'not found' in linkage or '/work/build-xacc' in linkage:
        raise ValueError('installed linkage')
    for key in ('consumer_sha256','installed_manifest_sha256'):
        if not re.fullmatch('[a-f0-9]{64}',report.get(key,'')):
            raise ValueError('output identity')
    if type(report.get('installed_files')) is not int or report['installed_files'] <= 0:
        raise ValueError('installed inventory')
    return {'native_passed': True, 'scope':'fresh XACC build and installed-only consumer',
            'builder_image':image, 'published':False,
            'complete_install_artifact_retained':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path);p.add_argument('manifest',type=Path)
    a=p.parse_args()
    print(json.dumps(verify(json.loads(a.report.read_text()),a.manifest.read_bytes()),indent=2))
