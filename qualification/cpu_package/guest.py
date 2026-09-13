"""Bounded native OCI build and existing image matrix on a disposable CPU VM."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import zlib

import stage

ROOT = Path('/work')


def run(command, timeout, log):
    start = time.monotonic()
    with log.open('wb') as output:
        process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT,
                                 timeout=timeout, env=dict(os.environ, DOCKER_BUILDKIT='0'))
    return {'exit': process.returncode, 'seconds': time.monotonic() - start,
            'log_sha256': stage.sha(log), 'tail': log.read_text(errors='replace')[-2000:]}


def emit(report):
    raw = json.dumps(report, sort_keys=True, separators=(',', ':')).encode()
    encoded = base64.b64encode(zlib.compress(raw, 9)).decode()
    if len(raw) > 120000 or len(encoded) > 128 * 160:
        raw = json.dumps({'kind': report['kind'], 'error': 'report_bounds'}, sort_keys=True).encode()
        encoded = base64.b64encode(zlib.compress(raw, 9)).decode()
    digest = hashlib.sha256(raw).hexdigest()
    parts = [encoded[i:i+160] for i in range(0, len(encoded), 160)]
    for repeat in range(2):
        for index, part in enumerate(parts):
            print(f'QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}', flush=True)


def main():
    report = {'kind': 'qb-cpu-oci-native-v1', 'published': False, 'stages': {}}
    try:
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        if (manifest['schema'] != 'marqov.cpu-native-input/v1'
                or set(manifest['files']) != {'stage.py', 'guest.py', 'qristal/qualification/runtime/test_image.py'}
                or manifest['context_sha256'] != stage.sha(ROOT / 'context/context.json')):
            raise ValueError('context_manifest_binding')
        for name, digest in manifest['files'].items():
            if stage.sha(ROOT / name) != digest:
                raise ValueError('harness_binding')
        report['manifest'] = manifest
        stage.verify_context(ROOT / 'context')
        report['context_sha256'] = stage.sha(ROOT / 'context/context.json')
        report['docker_version'] = subprocess.check_output(['docker', '--version'], text=True).strip()
        build = run(['docker', 'build', '--platform', 'linux/amd64', '--memory', '4g',
                     '--memory-swap', '4g', '--cpu-period', '100000', '--cpu-quota', '200000',
                     '--ulimit', 'nproc=256:256', '--iidfile', '/proof/image-id',
                     '/work/context'], 480, Path('/proof/build.log'))
        report['stages']['build'] = build
        if build['exit']:
            raise RuntimeError('image_build_failed')
        image = Path('/proof/image-id').read_text().strip()
        report['image'] = image
        observed = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image], text=True))[0]
        report['image_config'] = {key: observed['Config'].get(key) for key in ('User', 'Entrypoint', 'Cmd', 'WorkingDir')}
        report['image_inspected_id'] = observed['Id']
        checks = run(['python3', '-B', '/work/qristal/qualification/runtime/test_image.py',
                      '--image', image], 240, Path('/proof/checks.log'))
        report['stages']['checks'] = checks
        if (ROOT / 'image-tests.json').exists():
            report['tests'] = json.loads((ROOT / 'image-tests.json').read_text())
        report['logs'] = {p.name: {'sha256': stage.sha(p), 'tail': p.read_text(errors='replace')[-800:]}
                          for p in sorted(ROOT.glob('image-*.log'))}
        if checks['exit']:
            raise RuntimeError('image_checks_failed')
        report['native_passed'] = True
    except Exception as error:
        report['error'] = type(error).__name__ + ':' + str(error)
        for name in ('build', 'checks'):
            log = Path('/proof') / (name + '.log')
            if log.exists() and name not in report['stages']:
                report['stages'][name] = {'log_sha256': stage.sha(log), 'tail': log.read_text(errors='replace')[-2000:]}
    finally:
        emit(report)


if __name__ == '__main__':
    main()
