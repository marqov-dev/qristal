"""Static input check and pure-wheel verification; prepare never runs setup.py."""
import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
DIST = 'antlr4_python3_runtime-4.9.2.dist-info'
LIMIT = 8 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or str(path) != name or '\\' in name:
        raise ValueError('unsafe path')
    return name


def prepare(inputs, output):
    lock = json.loads((HERE / 'inputs.json').read_text())
    for name, expected in lock['artifacts'].items():
        path = inputs / name
        if path.is_symlink() or path.stat().st_size != expected['bytes'] or sha(path.read_bytes()) != expected['sha256']:
            raise ValueError('input identity')
    if not output.is_dir() or any(output.iterdir()):
        raise ValueError('output must be an empty directory')
    members, total, seen = [], 0, set()
    with tarfile.open(inputs / 'antlr4-python3-runtime-4.9.2.tar.gz', 'r:gz') as archive:
        for member in archive:
            name = safe(member.name)
            if name.split('/')[0] != 'antlr4-python3-runtime-4.9.2' or name in seen:
                raise ValueError('source root or duplicate')
            seen.add(name)
            if not (member.isdir() or member.isfile()) or member.mode & ~0o777:
                raise ValueError('special source member')
            total += member.size
            if total > LIMIT or len(seen) > 1000:
                raise ValueError('source bound')
            members.append((member, archive.extractfile(member).read() if member.isfile() else None))
    # All paths/types validated before writing; never use tar.extractall.
    for member, data in members:
        path = output / member.name
        if member.isdir():
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
            path.chmod(member.mode)
    identity = {'schema': 'qb.antlr-wheel-input/v1', 'built': False,
                'artifacts': lock['artifacts'],
                'recipe': {name: sha((HERE / name).read_bytes()) for name in ('recipe.py', 'build.sh', 'inputs.json')}}
    (output / 'input-identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    return identity


def verify(wheel):
    if wheel.name != 'antlr4_python3_runtime-4.9.2-py3-none-any.whl' or wheel.stat().st_size > LIMIT:
        raise ValueError('wheel name or size')
    files, total = {}, 0
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            name = safe(member.filename)
            mode = member.external_attr >> 16
            if name in files or member.is_dir() or mode & 0o170000 not in (0, 0o100000) or mode & 0o7000:
                raise ValueError('wheel member')
            total += member.file_size
            if total > LIMIT or len(files) >= 1000:
                raise ValueError('wheel bound')
            files[name] = archive.read(member)
    metadata = BytesParser().parsebytes(files[DIST + '/METADATA'])
    wheelmeta = BytesParser().parsebytes(files[DIST + '/WHEEL'])
    if metadata['Name'] != 'antlr4-python3-runtime' or metadata['Version'] != '4.9.2' or metadata['License'] != 'BSD':
        raise ValueError('package metadata')
    if wheelmeta['Root-Is-Purelib'] != 'true' or wheelmeta.get_all('Tag') != ['py3-none-any']:
        raise ValueError('pure wheel metadata')
    requirements = metadata.get_all('Requires-Dist', [])
    if len(requirements) != 1 or requirements[0].replace(' ', '').replace('"', "'") != "typing;python_version<'3.5'":
        raise ValueError('unexpected runtime requirement')
    if 'antlr4/__init__.py' not in files or 'antlr4_python3_runtime-4.9.2.data/scripts/pygrun' not in files:
        raise ValueError('required package or script')
    for name in files:
        if not (name.startswith('antlr4/') and name.endswith('.py') or name.startswith(DIST + '/')
                or name == 'antlr4_python3_runtime-4.9.2.data/scripts/pygrun'):
            raise ValueError('unexpected wheel payload')
    records = {}
    for name, digest, size in csv.reader(io.StringIO(files[DIST + '/RECORD'].decode())):
        if name in records or name not in files:
            raise ValueError('RECORD member')
        records[name] = True
        if name == DIST + '/RECORD':
            if digest or size:
                raise ValueError('RECORD self hash')
        elif digest != 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).decode().rstrip('=') or size != str(len(files[name])):
            raise ValueError('RECORD hash')
    if set(records) != set(files):
        raise ValueError('incomplete RECORD')
    return {'schema': 'qb.antlr-wheel-verification/v1', 'metadata_verified': True,
            'sha256': sha(wheel.read_bytes()), 'bytes': wheel.stat().st_size, 'files': len(files),
            'native_runtime_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify'))
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.input, args.output)
    else:
        result = verify(args.input)
        result['retained_logs'] = {name: sha((args.output / name).read_bytes()) for name in
                                   ('input-identity.json', 'tools.txt', 'pip-version.txt', 'build.log')}
        (args.output / 'wheel-verification.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
