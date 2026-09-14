"""Freeze or execute the exact QPP image probe; no cloud resource management."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f'
ARCHIVE_SHA = '451b0710cea596fcae3bf717caed723ab18677cab0e3354b11c3db9761a96ab5'
ARCHIVE_BYTES = 514349056
FILES = ('core_package/native_image.py', 'core_package/native_image_probe.py',
         'core_package/image_archive.py', 'core_package/local_probe.py',
         'core_package/wheel_linkage_guest.py', 'runtime/bounded_process.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition: raise ValueError(message)


def snapshot(source, target, limit, expected=None):
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as src, target.open('xb') as dst:
        before = os.fstat(src.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'regular bounded input required')
        h = hashlib.sha256(); size = 0
        while chunk := src.read(1024**2):
            size += len(chunk); require(size <= limit, 'input size bound')
            dst.write(chunk); h.update(chunk)
        after = os.fstat(src.fileno())
        require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'input changed')
        result = {'bytes': size, 'sha256': h.hexdigest()}
        require(expected is None or result == expected, 'input identity mismatch')
    target.chmod(0o644)
    return result


def prepare(archive, output):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'new output required')
    verifier = load('native_image_archive', HERE / 'image_archive.py')
    with tempfile.TemporaryDirectory(prefix='.native-image-', dir=output.parent) as tmp:
        root = Path(tmp) / 'bundle'; root.mkdir(); files = {}
        files['image.tar'] = snapshot(archive, root / 'image.tar', ARCHIVE_BYTES,
                                     {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA})
        proof = verifier.verify(root / 'image.tar', expected_sha256=ARCHIVE_SHA,
                                expected_bytes=ARCHIVE_BYTES, expected_image_id=IMAGE)
        for relative in FILES:
            name = 'qualification/' + relative
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            files[name] = snapshot(HERE.parent / relative, target, 1024**2)
        protocol = {'schema': 'qb.native-image-protocol/v1', 'image_index_digest': IMAGE,
                    'config_digest': proof['config_digest'], 'files': files,
                    'proposed_cloud': {'instance_type': 'm7i.large', 'region': 'us-east-1',
                        'root_gib': 20, 'observation_seconds': 3600, 'cleanup_seconds': 300,
                        'inbound_ports': [], 'workload_iam_profile': None, 'authorized': False},
                    'executed': False, 'hosted': False, 'redistribution_cleared': False}
        raw = (json.dumps(protocol, indent=2, sort_keys=True) + '\n').encode()
        (root / 'protocol.json').write_bytes(raw)
        output.mkdir(); os.replace(root, output)
        return {'protocol_sha256': hashlib.sha256(raw).hexdigest(), 'image_index_digest': IMAGE,
                'config_digest': proof['config_digest'], 'executed': False}


def loaded_matches(inspected, config, proof):
    require(isinstance(inspected, list) and len(inspected) == 1, 'loaded image cardinality')
    item = inspected[0]
    require(item.get('Id') in (proof['image_index_digest'], proof['config_digest']), 'loaded image identity')
    require(item.get('Architecture') == 'amd64' and item.get('Os') == 'linux', 'loaded platform')
    require(item.get('Config') == config['config'], 'loaded runtime config changed')
    require(item.get('RootFS') == {'Type': 'layers', 'Layers': config['rootfs']['diff_ids']}, 'loaded layers changed')
    return item['Id']


def execute(bundle, output, protocol_sha256):
    bundle, output = Path(bundle), Path(output)
    require(not output.exists(), 'new output required')
    require(platform.system() == 'Linux' and platform.machine() in ('x86_64', 'amd64'), 'Linux amd64 host required')
    require(not any(os.environ.get(key) for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')), 'Docker environment override forbidden')
    output.mkdir(mode=0o700)
    report = {'schema': 'qb.native-image-execution/v1', 'passed': False, 'commands': [],
              'protocol_sha256': protocol_sha256, 'hosted': False, 'redistribution_cleared': False,
              'cloud_instance_binding_verified': False, 'resource_cleanup_verified': False}
    bounded = load('native_image_bounded', HERE.parent / 'runtime/bounded_process.py')
    verifier = load('native_image_archive', HERE / 'image_archive.py')
    def command(args, seconds=30):
        record = {'command': args, 'timeout_seconds': seconds}
        report['commands'].append(record)
        try:
            code, out, err = bounded.capture(args, timeout=seconds, stdout_limit=1024**2, stderr_limit=65536)
            record.update(exit_code=code, stdout=out.decode(), stderr=err.decode())
            return code, out
        except Exception as error:
            record.update(error=type(error).__name__, complete_output_retained=False)
            raise
    try:
        with tempfile.TemporaryDirectory(prefix='qpp-native-frozen-') as tmp:
            private = Path(tmp)
            got = snapshot(bundle / 'protocol.json', private / 'protocol.json', 1024**2)
            require(got['sha256'] == protocol_sha256, 'protocol external identity')
            protocol = verifier.parse((private / 'protocol.json').read_bytes())
            require(protocol.get('schema') == 'qb.native-image-protocol/v1' and protocol.get('image_index_digest') == IMAGE, 'protocol identity')
            names = {'image.tar'} | {'qualification/' + name for name in FILES}
            require(set(protocol['files']) == names, 'protocol file set')
            for name, expected in protocol['files'].items():
                target = private / name; target.parent.mkdir(parents=True, exist_ok=True)
                snapshot(bundle / name, target, ARCHIVE_BYTES if name == 'image.tar' else 1024**2, expected)
            # Freeze the executing harness as well as guest inputs; reject a mixed checkout.
            for relative in FILES:
                require(hashlib.sha256((HERE.parent / relative).read_bytes()).hexdigest() ==
                        protocol['files']['qualification/' + relative]['sha256'], 'executing tool identity')
            proof = verifier.verify(private / 'image.tar', expected_sha256=ARCHIVE_SHA,
                                    expected_bytes=ARCHIVE_BYTES, expected_image_id=IMAGE)
            report['archive_verification'] = proof
            require(protocol['config_digest'] == proof['config_digest'], 'protocol config identity')
            with tarfile.open(private / 'image.tar') as tar:
                config = verifier.parse(tar.extractfile('blobs/sha256/' + proof['config_digest'][7:]).read(verifier.MAX_JSON + 1))
            code, endpoint = command(['docker', 'context', 'inspect', '--format', '{{if eq .Endpoints.docker.Host "unix:///var/run/docker.sock"}}local{{else}}unsupported{{end}}'])
            require(code == 0 and endpoint.strip() == b'local', 'local system Docker required')
            code, engine = command(['docker', 'info', '--format', '{{.OSType}} {{.Architecture}}'])
            require(code == 0 and engine.strip() in (b'linux x86_64', b'linux amd64'), 'native Docker engine required')
            report['host_architecture'] = platform.machine(); report['engine_platform'] = engine.decode().strip()
            for resource in ('image', 'container'):
                code, existing = command(['docker', resource, 'ls', '--all', '--quiet', '--no-trunc'])
                require(code == 0 and not existing.strip(), 'empty disposable Docker daemon required')
            report['empty_daemon_observed_before_load'] = True
            require(command(['docker', 'image', 'load', '--input', str(private / 'image.tar')], 180)[0] == 0, 'image load failed')
            selected = None
            for digest in (IMAGE, proof['config_digest']):
                code, raw = command(['docker', 'image', 'inspect', digest])
                if code == 0:
                    selected = loaded_matches(verifier.parse(raw), config, proof); break
            require(selected is not None, 'loaded immutable image unavailable')
            report['execution_digest'] = selected
            probe = load('native_image_probe', private / 'qualification/core_package/native_image_probe.py')
            report['probe'] = probe.run(selected, output / 'probes.json')
            report['passed'] = report['probe'].get('passed') is True
    except Exception as error:
        report['error'] = type(error).__name__ + ':' + str(error)
    finally:
        (output / 'execution.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('archive', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('execute'); p.add_argument('bundle', type=Path); p.add_argument('output', type=Path); p.add_argument('--protocol-sha256', required=True)
    args = vars(parser.parse_args()); action = args.pop('command')
    result = prepare(**args) if action == 'prepare' else execute(**args)
    print(json.dumps(result if action == 'prepare' else {'passed': result['passed']}))
    if action == 'execute' and not result['passed']: raise SystemExit(1)
