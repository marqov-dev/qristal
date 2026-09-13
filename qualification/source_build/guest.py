"""Fresh offline XACC build on a disposable host; bounded console evidence."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zlib

ROOT = Path('/work')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, seconds, name):
    log = Path('/proof') / (name + '.log')
    start = time.monotonic()
    timeout = False
    with log.open('wb') as output:
        try:
            p = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=seconds)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code = None
            timeout = True
    return {'command': command, 'exit': code, 'timeout': timeout, 'seconds': time.monotonic() - start,
            'log_sha256': sha(log), 'tail': log.read_text(errors='replace')[-2200:]}


def emit(report):
    raw = json.dumps(report, sort_keys=True, separators=(',', ':')).encode()
    data = base64.b64encode(zlib.compress(raw, 9)).decode()
    if len(data) > 128 * 160:
        raw = json.dumps({'kind': report['kind'], 'error': 'report_bounds'}).encode()
        data = base64.b64encode(zlib.compress(raw, 9)).decode()
    digest = hashlib.sha256(raw).hexdigest()
    parts = [data[i:i+160] for i in range(0, len(data), 160)]
    for _ in range(2):
        for n, part in enumerate(parts):
            print('QB_ADAPTER_CHUNK', digest, n, len(parts), part, flush=True)


def main():
    report = {'kind': 'qb-xacc-fresh-source-v1', 'stages': {}, 'native_passed': False}
    owned = None
    try:
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        if manifest['schema'] != 'qb.source-build-input/v1':
            raise ValueError('schema')
        report['manifest_sha256'] = sha(ROOT / 'manifest.json')
        for name, info in manifest['files'].items():
            path = ROOT / name
            if 'directory' in info:
                if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o777 != info['directory']:
                    raise ValueError('input_directory')
            elif 'link' in info:
                if not path.is_symlink() or str(path.readlink()) != info['link']:
                    raise ValueError('input_link')
            elif path.is_symlink() or sha(path) != info['sha256'] or path.stat().st_mode & 0o777 != info['mode']:
                raise ValueError('input_file')
        # Build only the toolchain context. No source or installed binary enters it.
        toolchain = Path('/proof/toolchain'); toolchain.mkdir()
        for name in ('Dockerfile', 'install-toolchain.sh'):
            (toolchain / name).write_bytes((ROOT / name).read_bytes())
        result = run(['docker', 'build', '--iidfile', '/proof/builder-id', str(toolchain)], 600, 'builder')
        report['stages']['builder'] = result
        if result['exit'] != 0:
            raise RuntimeError('builder_failed')
        image = Path('/proof/builder-id').read_text().strip()
        report['builder_image'] = image
        for name in ('build-xacc', 'install-xacc'):
            (ROOT / name).mkdir()
            (ROOT / name).chmod(0o777)
        def container(command, limit, name, installed=False):
            nonlocal owned
            owned = 'qb-source-' + name
            cmd = ['docker','run','--name',owned,'--network','none','--read-only','--cpus','2',
                   '--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL',
                   '--security-opt','no-new-privileges','--user','65532:65532','--tmpfs','/tmp:rw,exec,size=512m',
                   '--workdir','/tmp']
            paths = ['install-xacc'] if installed else ['xacc','googletest','archives','acz_qpp_smoke.cpp','build-xacc','install-xacc']
            for item in paths:
                writable = item in ('build-xacc','install-xacc') and not installed
                cmd += ['--mount','type=bind,source=/work/'+item+',target=/work/'+item+('' if writable else ',readonly')]
            if installed:
                cmd += ['--mount','type=bind,source=/proof/consumer,target=/consumer,readonly']
                cmd += ['--mount','type=bind,source=/proof/consumer-output,target=/consumer-output' + ('' if name == 'consumer-build' else ',readonly')]
            cmd += ['--entrypoint','/usr/bin/env',image,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2'] + command
            result = run(cmd, limit, name)
            stopped = subprocess.run(['docker','rm','-f',owned], capture_output=True, timeout=30).returncode == 0
            absent = subprocess.run(['docker','inspect',owned],capture_output=True,timeout=15).returncode != 0
            owned = None
            result['container_removed'] = stopped and absent
            report['stages'][name] = result
            if result['exit'] != 0 or not result['container_removed']:
                raise RuntimeError(name + '_failed')
            return result
        configure = ['cmake','-S','/work/xacc','-B','/work/build-xacc','-DCMAKE_INSTALL_PREFIX=/work/install-xacc',
            '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DMARQOV_CPU_PROBE=ON',
            '-DXACC_BUILD_TESTS=OFF','-DINSTALL_GTEST=OFF','-DXACC_BUILD_EXAMPLES=OFF','-DXACC_ENABLE_MPI=OFF',
            '-DGIT_SUBMODULE=OFF','-DCMAKE_DISABLE_FIND_PACKAGE_Python=TRUE',
            '-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=/work/googletest','-DBOOST_ARCHIVE_DIRECTORY=/work/archives',
            '-DBOOST_DOWNLOAD_TO_BINARY_DIR=ON','-DCPR_USE_SYSTEM_CURL=ON','-DCMAKE_IGNORE_PREFIX_PATH=/opt/qb;/mnt/qb']
        container(['sh','-c','c++ --version; cmake --version; python3 --version; cat /toolchain-packages.txt'],60,'inventory')
        container(configure,300,'configure')
        container(['cmake','--build','/work/build-xacc','--parallel','2'],900,'build')
        container(['/work/build-xacc/marqov-acz-qpp'],60,'build-test')
        container(['cmake','--install','/work/build-xacc'],120,'install')
        # Compile a separate consumer using installed headers/libraries only.
        Path('/proof/consumer').mkdir()
        Path('/proof/consumer-output').mkdir()
        Path('/proof/consumer-output').chmod(0o777)
        Path('/proof/consumer/acz.cpp').write_bytes((ROOT / 'acz_qpp_smoke.cpp').read_bytes())
        container(['c++','-std=c++17','-O1','-DNDEBUG','/consumer/acz.cpp',
                   '-I/work/install-xacc/include/xacc','-I/work/install-xacc/include',
                   '-I/work/install-xacc/include/cppmicroservices4','-L/work/install-xacc/lib',
                   '-Wl,-rpath,/work/install-xacc/lib','-lxacc','-lCppMicroServices','-ldl','-lpthread',
                   '-o','/consumer-output/acz'],120,'consumer-build',True)
        report['consumer_sha256'] = sha(Path('/proof/consumer-output/acz'))
        linkage = container(['ldd','/consumer-output/acz'],60,'installed-linkage',True)
        if 'not found' in linkage['tail'] or '/work/build-xacc' in linkage['tail']:
            raise RuntimeError('installed_linkage')
        test = container(['/consumer-output/acz','--installed'],60,'installed-test',True)
        if 'PASS: ACZ registered' not in test['tail'] or '[error]' in test['tail']:
            raise RuntimeError('installed_test_marker')
        installed = {str(p.relative_to(ROOT/'install-xacc')):sha(p) for p in sorted((ROOT/'install-xacc').rglob('*')) if p.is_file() and not p.is_symlink()}
        report['installed_files'] = len(installed)
        report['installed_manifest_sha256'] = hashlib.sha256(json.dumps(installed,sort_keys=True).encode()).hexdigest()
        report['installed_libraries'] = {n:h for n,h in installed.items() if n.endswith('.so')}
        report['native_passed'] = True
    except Exception as error:
        report['error'] = type(error).__name__ + ':' + str(error)
    finally:
        if owned:
            subprocess.run(['docker','rm','-f',owned],capture_output=True,timeout=30)
        emit(report)


if __name__ == '__main__':
    main()
