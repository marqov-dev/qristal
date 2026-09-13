"""Verify exact material inventory and bytes before native build commands."""
import hashlib
import json
from pathlib import Path
import stat
import sys


def inventory(root, *, exclude_manifest=False):
    entries = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if exclude_manifest and name == 'material-manifest.json':
            continue
        mode = path.lstat().st_mode
        if stat.S_IMODE(mode) & 0o7000:
            raise ValueError('special material mode')
        if path.is_symlink():
            target = str(path.readlink())
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root.resolve()):
                raise ValueError('escaping material link')
            # Symlink permission bits are host-specific and cannot be set on Linux.
            entries[name] = {'type':'link','target':target}
        elif path.is_dir():
            entries[name] = {'type':'directory','mode':stat.S_IMODE(mode)}
        elif path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while data := stream.read(1024 * 1024): digest.update(data)
            entries[name] = {'type':'file','mode':stat.S_IMODE(mode),'bytes':path.stat().st_size,'sha256':digest.hexdigest()}
        else:
            raise ValueError('special material')
    return entries


def verify(root):
    manifest = root / 'material-manifest.json'
    if manifest.is_symlink(): raise ValueError('linked material manifest')
    expected = json.loads(manifest.read_text())
    if expected.get('schema') != 'qb.core-material-manifest/v1' or inventory(root, exclude_manifest=True) != expected['entries']:
        raise ValueError('material inventory mismatch')
    return {'verified':True,'entries':len(expected['entries']),
            'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]).resolve()),sort_keys=True))
