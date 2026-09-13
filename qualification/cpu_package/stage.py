"""Capture and verify explicit CPU payload bytes, then stage an OCI build context.

Does not compile, run Docker, acquire dependencies or claim source provenance.
"""
import argparse
import hashlib
import json
import os
import posixpath
from pathlib import Path
import shutil
import stat

HERE = Path(__file__).resolve().parent
# Source paths are relative to the isolated installed-runtime workspace.
INPUTS = {
    'install-core/lib': 'work/install-core/lib',
    'install-xacc/lib': 'work/install-xacc/lib',
    'install-xacc/plugins': 'work/install-xacc/plugins',
    'home/.local/lib/python3.10/site-packages': 'runtime/python-core',
    'integration-deps': 'runtime/python-integration',
    'install-integrations': 'work/install-integrations',
    'installed-checks': 'checks',
    'runtime-probe/decoder-smoke': 'probe/decoder-smoke',
    'qristal/LICENSE': 'opt/qristal/LICENSE.source',
    'runtime-image-input/licenses': 'opt/qristal/licenses',
    'qristal/qualification/runtime/runtime.py': 'opt/qristal/runtime.py',
    'qristal/qualification/runtime/adapter.py': 'opt/qristal/adapter.py',
    'qristal/qualification/runtime/capabilities.json': 'opt/qristal/capabilities.json',
    'qristal/qualification/runtime/bell.qasm': 'checks/bell.qasm',
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(path):
    """Include directories/modes and link text; never traverse symbolic links."""
    records = {}
    def visit(item, name):
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = os.readlink(item)
            records[name] = {'type': 'link', 'target': target}
        elif stat.S_ISDIR(mode):
            records[name] = {'type': 'directory', 'mode': stat.S_IMODE(mode)}
            for child in sorted(item.iterdir()):
                visit(child, child.name if name == '.' else name + '/' + child.name)
        elif stat.S_ISREG(mode):
            records[name] = {'type': 'file', 'mode': stat.S_IMODE(mode), 'sha256': sha(item)}
        else:
            raise ValueError('special input file: ' + name)
    if path.is_symlink():
        raise ValueError('input root must not be a symlink')
    visit(path, '.')
    return records


def validate_links(records):
    """Resolve only declared container paths, never absolute paths on the host.

Directory symlinks are deliberately unsupported to keep COPY traversal explicit.
"""
    for name, entry in records.items():
        if entry['type'] != 'link':
            continue
        seen = set()
        current = name
        while records.get(current, {}).get('type') == 'link':
            if current in seen:
                raise ValueError('cyclic payload symlink: ' + name)
            seen.add(current)
            target = records[current]['target']
            if '..' in target.split('/'):
                raise ValueError('parent traversal symlink unsupported: ' + name)
            current = posixpath.normpath(posixpath.join('/', posixpath.dirname(current), target)).lstrip('/')
        if records.get(current, {}).get('type') != 'file':
            raise ValueError('symlink target is not a declared payload file: ' + name)


def layout(inputs):
    records = {}
    for record in inputs.values():
        for name, entry in record['entries'].items():
            target = record['destination'] if name == '.' else record['destination'] + '/' + name
            records[target] = entry
    return records


def capture(workspace):
    workspace = workspace.resolve()
    result = {}
    for source, destination in INPUTS.items():
        path = workspace / source
        if not path.resolve().is_relative_to(workspace):
            raise ValueError('input escapes workspace')
        result[source] = {'destination': destination, 'entries': inventory(path)}
    validate_links(layout(result))
    return {'schema': 'marqov.cpu-inputs/v1',
            'provenance': 'observed_installed_bytes_not_verified_build_origin',
            'inputs': result}


def stage(workspace, receipt, output):
    workspace = workspace.resolve()
    output = output.resolve()
    if output.is_relative_to(workspace):
        raise ValueError('output must be outside the installed workspace')
    if output.exists():
        raise ValueError('output must be new')
    if receipt != capture(workspace):
        raise ValueError('installed inputs differ from receipt')
    output.mkdir(parents=True)
    payload = output / 'payload'
    for source, record in receipt['inputs'].items():
        src, dst = workspace / source, payload / record['destination']
        missing = []
        parent = dst.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        dst.parent.mkdir(parents=True, exist_ok=True)
        for parent in missing:
            parent.chmod(0o755)
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            if dst.is_symlink():
                dst.unlink()  # Replace only the staged link; never follow its target.
            if dst.is_dir():
                raise ValueError('file destination is a directory')
            shutil.copy2(src, dst)
        if inventory(dst) != record['entries']:
            raise ValueError('copied input differs from receipt: ' + source)
    # Bell is explicitly overlaid from the current harness. Verify the final tree
    # separately as that overlap may differ from an older installed-checks copy.
    final = inventory(payload)
    validate_links(final)
    for name, entry in final.items():
        required = 0o5 if entry['type'] == 'directory' else 0o4
        if entry['type'] != 'link' and entry['mode'] & required != required:
            raise ValueError('payload inaccessible to runtime UID: ' + name)
    (output / 'payload-inventory.json').write_text(json.dumps(final, indent=2) + '\n')
    (output / 'inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')
    shutil.copy2(HERE / 'Dockerfile', output / 'Dockerfile')
    shutil.copy2(HERE.parent / 'runtime/apt-runtime.txt', output / 'apt-runtime.txt')
    files = ['Dockerfile', 'apt-runtime.txt', 'inputs.json', 'payload-inventory.json']
    (output / 'context.json').write_text(json.dumps({
        'schema': 'marqov.cpu-context/v1', 'files': {p: sha(output / p) for p in files},
        'native_qualified': False, 'published': False}, indent=2) + '\n')


def verify_context(output):
    record = json.loads((output / 'context.json').read_text())
    expected = {'Dockerfile', 'apt-runtime.txt', 'inputs.json', 'payload-inventory.json'}
    if (record['schema'] != 'marqov.cpu-context/v1' or set(record['files']) != expected
            or record['native_qualified'] is not False or record['published'] is not False):
        raise ValueError('context boundary')
    if set(p.name for p in output.iterdir()) != expected | {'context.json', 'payload'}:
        raise ValueError('unexpected context input')
    if any(sha(output / p) != digest for p, digest in record['files'].items()):
        raise ValueError('context metadata mismatch')
    validate_links(inventory(output / 'payload'))
    if inventory(output / 'payload') != json.loads((output / 'payload-inventory.json').read_text()):
        raise ValueError('payload mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['capture', 'stage', 'verify'])
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        verify_context(args.output)
    elif args.workspace is None:
        parser.error('--workspace is required')
    elif args.action == 'capture':
        data = capture(args.workspace)
        with args.output.open('x') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
    else:
        if args.receipt is None:
            parser.error('--receipt is required')
        stage(args.workspace, json.loads(args.receipt.read_text()), args.output)
        verify_context(args.output)


if __name__ == '__main__':
    main()
