"""Read-only gate for future QPP packaging; never extract, build or publish."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
QUALIFICATION = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OUTPUT = load('packaging_core_output', QUALIFICATION / 'core_output/output.py')
NATIVE = load('packaging_core_native', QUALIFICATION / 'core_native/check_result.py')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data := stream.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def document(path, *, limit=2 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('invalid or oversized receipt')
    return parse(path.read_bytes())


def audit(archive, protocol_path, native_receipt, material_manifest):
    archive, protocol_path, native_receipt, material_manifest = map(Path, (archive, protocol_path, native_receipt, material_manifest))
    protocol = document(protocol_path)
    envelope = document(native_receipt)
    report = envelope.get('result', envelope)
    if (protocol.get('schema') != 'qb.core-native-protocol/v1'
            or not isinstance(report, dict) or report.get('native_passed') is not True
            or report.get('error') or report.get('output_artifact_error')):
        raise ValueError('successful native evidence required')
    materials = document(material_manifest, limit=32 * 1024 * 1024)
    materials_sha = sha(material_manifest)
    if materials.get('schema') != 'qb.core-material-manifest/v1' or materials_sha != protocol.get('materials_sha256'):
        raise ValueError('executed material manifest identity')
    entries = materials.get('entries')
    if not isinstance(entries, dict):
        raise ValueError('material entries')
    wheel_manifest = QUALIFICATION / 'evidence/2026-09-13-python-artifacts/core.json'
    wheel_manifest_bytes = wheel_manifest.read_bytes()
    wheels = parse(wheel_manifest_bytes)['wheels']
    if (len(wheels) != 50 or len({item['filename'] for item in wheels}) != 50
            or len({item['name'].lower().replace('_', '-') for item in wheels}) != 50):
        raise ValueError('unexpected or duplicate required wheel set')
    def file_binding(name, size, digest):
        entry = entries.get(name, {})
        if (entry.get('type') != 'file' or type(entry.get('bytes')) is not int
                or entry['bytes'] != size or entry.get('sha256') != digest):
            raise ValueError('material file identity: ' + name)
    wheel_manifest_sha = hashlib.sha256(wheel_manifest_bytes).hexdigest()
    file_binding('python/core.json', len(wheel_manifest_bytes), wheel_manifest_sha)
    names = {'python/wheels/' + item['filename'] for item in wheels}
    if ({name for name in entries if name.startswith('python/wheels/')} != names
            or entries.get('python/wheels', {}).get('type') != 'directory'):
        raise ValueError('missing or extra material wheel')
    for item in wheels:
        file_binding('python/wheels/' + item['filename'], item['bytes'], item['sha256'])
    # Reuse only the exact validators bound by the executed protocol. A changed
    # validator requires its own reviewed compatibility decision, not inference.
    validators = ('core_output/output.py', 'core_native/check_result.py')
    for name in validators:
        if protocol.get('operator_files', {}).get(name) != sha(QUALIFICATION / name):
            raise ValueError('executed validator identity mismatch')
    if archive.is_symlink() or not archive.is_file():
        raise ValueError('archive must be a regular file')
    identity = report.get('output_artifact')
    if not isinstance(identity, dict):
        raise ValueError('missing output identity')
    original = {key: value for key, value in report.items() if key != 'output_artifact'}
    verified = OUTPUT.verify(archive, identity, original)
    if verified.get('verified') is not True:
        raise ValueError('archive did not verify')
    classified = NATIVE.classify(report, protocol_path, archive)
    if classified.get('native_passed') is not True:
        raise ValueError('native classification failed')
    # Security rules already enforced above. Read only the validated receipt to
    # expose its inventory; do not implement another extractor/link policy.
    receipt = None
    with tarfile.open(archive, 'r|gz') as stream:
        for member in stream:
            if member.name == 'receipt.json':
                if member.size > 32 * 1024 * 1024:
                    raise ValueError('inventory receipt bound')
                receipt = parse(stream.extractfile(member).read())
                break
    if receipt is None:
        raise ValueError('verified archive receipt missing')
    final_archive_sha = sha(archive)
    if final_archive_sha != identity['sha256']:
        raise ValueError('archive changed during audit')
    inventory = receipt['entries']
    antlr_name = 'antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl'
    antlr = inventory[antlr_name]
    if antlr.get('type') != 'file':
        raise ValueError('ANTLR inventory missing')
    return {
        'schema': 'qb.core-packaging-input-plan/v1', 'input_gate_passed': True,
        'runtime_built': False, 'runtime_qualified': False, 'published': False, 'hosted': False,
        'scope': 'QPP-only CPU packaging input; no Aer/Integrations/Decoder qualification',
        'bindings': {'archive_sha256': final_archive_sha, 'archive_bytes': archive.stat().st_size,
                     'protocol_sha256': sha(protocol_path), 'native_receipt_sha256': sha(native_receipt),
                     'material_manifest_sha256': materials_sha,
                     'validator_files': {name: sha(QUALIFICATION / name) for name in validators},
                     'audit_sha256': sha(__file__), 'required_wheel_manifest_sha256': wheel_manifest_sha},
        'native_classification': classified,
        'retained_inventory': inventory,
        'required_python': {'implementation': 'CPython', 'version': '3.10', 'platform': 'linux/amd64',
                            'wheel_install_verified': False,
                            'wheels': [{key: item[key] for key in ('name', 'version', 'filename', 'bytes', 'sha256')} for item in wheels],
                            'antlr': dict(antlr, archive_path=antlr_name),
                            'installation': 'fresh environment; local wheels only; --no-index --no-deps --require-hashes; pip check'},
        'required_runtime': {'status': 'not assembled', 'install_paths': ['/work/install-core', '/work/install-xacc'],
                             'preserve_normalized_sibling_links': True,
                             'adapter_sources_to_bind': ['qualification/runtime/runtime.py', 'qualification/runtime/adapter.py'],
                             'capabilities_change_required': 'declare only QPP until additional native matrix passes',
                             'notices_required': 'collect from exact verified Core/XACC/dependency sources and Python/OS distributions'},
        'required_system_abi': {'status': 'must select and qualify final runtime',
                                'builder_image_observed': report.get('builder_image'),
                                'inventory_log': 'logs/inventory.log', 'linkage_log': 'logs/installed-linkage.log',
                                'components': ['CPython3.10 shared library', 'libstdc++', 'libgomp', 'OpenBLAS', 'libgfortran', 'curl', 'OpenSSL'],
                                'historical_reference_only': 'qualification/runtime/apt-runtime.txt',
                                'gate': 'pin final OS package bytes or snapshot; verify ELF/Python imports and installed-only replay'},
        'remaining_gates': ['verified staging without source/build mounts', 'final image QPP adapter and isolation matrix',
                            'notices and complete package inventory', 'immutable candidate build and acquired-digest replay',
                            'separate reproducibility comparison and hosted admission'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('native_receipt', type=Path)
    parser.add_argument('material_manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.archive, args.protocol, args.native_receipt, args.material_manifest)
    # Successful evidence only, and never overwrite an existing plan.
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('input_gate_passed', 'runtime_built', 'runtime_qualified', 'published', 'hosted')}))


if __name__ == '__main__':
    main()
