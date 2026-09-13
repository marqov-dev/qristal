"""Classify retained CPU OCI results; recovery alone is not a passing test."""
import json
import re
from pathlib import Path

import stage

HERE = Path(__file__).resolve().parent


def expected_command(name, container, image):
    command = ['docker','run','--rm','--name',container,'--platform','linux/amd64',
               '--network','none','--cpus','2','--memory','4g','--memory-swap','4g',
               '--pids-limit','256','--read-only','--tmpfs','/tmp:rw,exec,size=128m',
               '--cap-drop','ALL','--security-opt','no-new-privileges']
    fixtures = {'core':'core_cpu_smoke.py','noise':'core_noise_smoke.py','integration':'integration_smoke.py'}
    entry = None
    if name in fixtures:
        entry = 'python3'
        args = ['-s','-B','/checks/isolation.py',fixtures[name]]
    elif name == 'decoder':
        entry, args = '/probe/decoder-smoke', []
    elif name == 'isolation':
        entry = 'python3'
        args = ['-c', "import os,pathlib; assert os.getuid()==65532; assert not pathlib.Path('/work/build-core').exists(); assert not pathlib.Path('/usr/bin/c++').exists(); print('PASS: non-root, no build tree or compiler')"]
    else:
        args = {'capabilities':['--capabilities'], 'bell':['--qasm','/checks/bell.qasm'],
                'noisy-bell':['--qasm','/checks/bell.qasm','--backend','aer','--readout-p10','.2','--readout-p01','.1'],
                'reject-shots':['--qasm','/checks/bell.qasm','--shots','16385'],
                'reject-gpu':['--backend','gpu']}[name]
    if entry:
        command += ['--entrypoint',entry]
    if name == 'integration':
        command += ['-e','PYTHONPATH=/work/install-core/lib:/runtime/python-integration:/work/install-integrations']
    return command + [image] + args


def verify(report, manifest):
    if report.get('kind') != 'qb-cpu-oci-native-v1':
        raise ValueError('report_kind')
    if report.get('error') or report.get('bootstrap_exit_code'):
        return {'native_passed': False, 'reason': report.get('error', 'bootstrap_failed')}
    if (manifest.get('schema') != 'marqov.cpu-native-input/v1' or report.get('manifest') != manifest or report.get('context_sha256') != manifest['context_sha256']
            or report.get('published') is not False):
        raise ValueError('manifest_binding')
    expected_files = {'stage.py': HERE / 'stage.py', 'guest.py': HERE / 'guest.py',
                      'qristal/qualification/runtime/test_image.py': HERE.parent / 'runtime/test_image.py'}
    if manifest['files'] != {name: stage.sha(path) for name, path in expected_files.items()}:
        raise ValueError('harness_binding')
    image = report['image']
    if (image != report['image_inspected_id'] or image != report['tests']['image']
            or not re.fullmatch(r'sha256:[a-f0-9]{64}', image)):
        raise ValueError('image_identity')
    if report.get('image_config') != {'User':'65532:65532','Entrypoint':['python3','/opt/qristal/runtime.py'],
                                      'Cmd':['--capabilities'],'WorkingDir':'/tmp'}:
        raise ValueError('image_configuration')
    if report.get('native_passed') is not True or report['tests']['no_host_mounts'] is not True:
        raise ValueError('native_verdict')
    if any(report['stages'][name]['exit'] != 0 for name in ('build', 'checks')):
        raise ValueError('stage_failed')
    tests = report['tests']['tests']
    expected = {'capabilities','core','noise','integration','decoder','bell','noisy-bell','reject-shots','reject-gpu','isolation'}
    if len(tests) != 10 or {test['name'] for test in tests} != expected:
        raise ValueError('test_set')
    for test in tests:
        command = test['command']
        container = command[4] if len(command) > 4 else ''
        if (test['exit'] != (2 if test['name'].startswith('reject-') else 0)
                or not re.fullmatch(r'marqov-runtime-test-[a-f0-9]{10}', container)
                or command != expected_command(test['name'], container, image)):
            raise ValueError('test_verdict')
    return {'native_passed': True, 'image': image, 'published': False, 'test_groups': 10}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.report.read_text()), json.loads(args.manifest.read_text())), indent=2))
