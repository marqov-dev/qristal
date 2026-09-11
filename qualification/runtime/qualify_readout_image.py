"""Qualify a source overlay on the existing local image; no build/pull/push or cloud."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from bounded_process import capture

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44'
FILES = ('adapter.py', 'bounded_process.py', 'candidate.py', 'program_guard.py',
         'preparation_binding.py', 'runtime.py', 'local_pipeline.py', 'readout_demo.py',
         'test_readout_pipeline.py', 'test_local_pipeline.py', 'test_preparation_binding.py',
         'test_program_guard.py', 'test_candidate.py', 'test_bounded_process.py')
TESTS = ('test_readout_pipeline', 'test_local_pipeline', 'test_preparation_binding',
         'test_program_guard', 'test_candidate', 'test_bounded_process')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, data):
    with path.open('xb') as stream:
        stream.write(data)


def docker(*args):
    return subprocess.check_output(['docker', *args], stderr=subprocess.PIPE, timeout=30)


def run_stage(output, label):
    name = 'qristal-readout-' + uuid.uuid4().hex
    write(output / (label + '-intent.json'), json.dumps({'name': name, 'image': IMAGE}).encode())
    def owned():
        return docker('ps', '-aq', '--filter', f'name=^/{name}$',
                      '--filter', f'label=qristal.readout={name}').decode().split()
    sources = {file: (HERE / file).read_text() for file in FILES}
    bootstrap = "import pathlib,sys,runpy,hashlib\n"
    bootstrap += "sources = " + repr(sources) + "\n"
    bootstrap += """for name in ('adapter.py', 'runtime.py'):
    if pathlib.Path('/opt/qristal', name).read_bytes() != sources[name].encode():
        raise ValueError('native_cli_source_mismatch')
base = pathlib.Path('/tmp/readout-overlay')
base.mkdir()
for name, source in sources.items():
    (base / name).write_text(source)
sys.path.insert(0, str(base))
"""
    if label == 'tests':
        bootstrap += "sys.argv = " + repr(['unittest', *TESTS]) + "\n"
        bootstrap += "runpy.run_module('unittest', run_name='__main__')\n"
    else:
        bootstrap += "runpy.run_path(str(base / 'readout_demo.py'), run_name='__main__')\n"
    try:
        docker('create' , '--pull', 'never', '--name', name, '--label', f'qristal.readout={name}',
               '--platform', 'linux/amd64', '--network', 'none', '--cpus', '2', '--memory', '4g',
               '--memory-swap', '4g', '--pids-limit', '256', '--read-only', '--tmpfs', '/tmp:rw,exec,size=128m',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '65532:65532',
               '--workdir', '/opt/qristal', '--entrypoint', 'python3', IMAGE, '-B', '-c', bootstrap)
        code, stdout, stderr = capture(['docker', 'start', '-a', name], timeout=240,
                                       stdout_limit=131072, stderr_limit=16384)
        write(output / (label + '.stdout'), stdout)
        write(output / (label + '.stderr'), stderr)
        if code:
            raise RuntimeError(label + '_failed')
        if label == 'demo' and stderr:
            raise RuntimeError('unexpected_demo_stderr')
        return stdout
    finally:
        for identity in owned():
            docker('rm', '-f', identity)
        if owned():
            raise RuntimeError('cleanup_failed')
        write(output / (label + '-cleanup.json'), json.dumps({'name': name, 'absent': True}).encode())


def qualify(output):
    output.mkdir(mode=0o700)
    inspected = json.loads(docker('image', 'inspect', IMAGE))[0]
    if inspected['Id'] != IMAGE or inspected['Architecture'] != 'amd64':
        raise ValueError('image_mismatch')
    run_stage(output, 'tests')
    report = json.loads(run_stage(output, 'demo'))
    if len(report['fixtures']) != 11:
        raise ValueError('demo_incomplete')
    manifest = {'profile': 'restricted-cpu-readout-qualification-v0', 'parent_image': IMAGE,
                'overlay_sources': {name: sha((HERE / name).read_bytes()) for name in FILES},
                'harness_sha256': sha(Path(__file__).read_bytes()),
                'source_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE).decode().strip(),
                'files': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
                'native_rebuild': False, 'registry_published': False, 'cloud_execution': False}
    write(output / 'manifest.json', json.dumps(manifest, indent=2, sort_keys=True).encode() + b'\n')
    print(json.dumps({'status': 'passed', 'fixtures': len(report['fixtures']),
                      'parent_image': IMAGE, 'owned_containers_absent': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    qualify(parser.parse_args().output)
