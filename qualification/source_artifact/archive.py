"""Bounded output receipt; verify tar members without extracting any path."""
import hashlib
import json
import posixpath
import stat
import tarfile
from pathlib import Path, PurePosixPath

MAX_BYTES = 1024 * 1024 * 1024
MAX_MEMBERS = 50000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def safe_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p) != name or '\\' in name:
        raise ValueError('unsafe member name')
    return name


def safe_link(name, target):
    if not target or target.startswith('/') or '\\' in target:
        raise ValueError('unsafe link')
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
    if resolved == '..' or resolved.startswith('../'):
        raise ValueError('escaping link')


def pack(output, report, roots):
    """Called outside workloads; only explicitly named public-output roots enter tar."""
    entries, files = {}, {}
    total = 0
    for prefix, root in roots.items():
        safe_name(prefix)
        root = Path(root)
        if not root.exists() or root.is_symlink():
            raise ValueError('missing or linked root')
        for path in [root] + sorted(root.rglob('*')):
            name = prefix if path == root else prefix + '/' + path.relative_to(root).as_posix()
            safe_name(name)
            mode = stat.S_IMODE(path.lstat().st_mode)
            if mode & 0o7000:
                raise ValueError('special mode')
            if path.is_symlink():
                target = str(path.readlink())
                safe_link(name, target)
                info = {'type': 'symlink', 'mode': mode, 'target': target}
            elif path.is_dir():
                info = {'type': 'directory', 'mode': mode}
            elif path.is_file():
                size = path.stat().st_size
                total += size
                if total > MAX_BYTES:
                    raise ValueError('output byte bound')
                info = {'type': 'file', 'mode': mode, 'size': size, 'sha256': digest(path.read_bytes())}
            else:
                raise ValueError('special file')
            entries[name] = info
            files[name] = path
            if len(entries) > MAX_MEMBERS:
                raise ValueError('output member bound')
    raw_report = canonical(report)
    entries['report.json'] = {'type': 'file', 'mode': 0o644, 'size': len(raw_report), 'sha256': digest(raw_report)}
    receipt = {'schema': 'qb.source-artifact/v1', 'report_sha256': digest(raw_report), 'entries': entries}
    import io
    with tarfile.open(output, 'w:gz', dereference=False) as archive:
        for name, path in files.items():
            archive.add(path, arcname=name, recursive=False)
        for name, data in [('report.json', raw_report), ('receipt.json', canonical(receipt))]:
            member = tarfile.TarInfo(name)
            member.mode, member.size = 0o644, len(data)
            archive.addfile(member, io.BytesIO(data))
    if Path(output).stat().st_size > MAX_BYTES:
        raise ValueError('compressed output bound')
    return {'sha256': digest(Path(output).read_bytes()), 'bytes': Path(output).stat().st_size,
            'report_sha256': digest(raw_report), 'receipt_sha256': digest(canonical(receipt))}


def verify(path, expected, report):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES or path.stat().st_size != expected['bytes']:
        raise ValueError('archive size')
    if digest(path.read_bytes()) != expected['sha256']:
        raise ValueError('archive hash')
    entries, special, total = {}, {}, 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            name = safe_name(member.name)
            if name in entries or name in special or len(entries) >= MAX_MEMBERS + 2:
                raise ValueError('duplicate or excessive members')
            if member.mode & ~0o777:
                raise ValueError('special mode')
            if member.isfile():
                total += member.size
                if total > MAX_BYTES or member.size < 0:
                    raise ValueError('expanded byte bound')
                data = archive.extractfile(member).read()
                info = {'type': 'file', 'mode': member.mode, 'size': member.size, 'sha256': digest(data)}
                if name in ('receipt.json', 'report.json'):
                    special[name] = data
            elif member.isdir():
                info = {'type': 'directory', 'mode': member.mode}
            elif member.issym():
                safe_link(name, member.linkname)
                info = {'type': 'symlink', 'mode': member.mode, 'target': member.linkname}
            else:
                raise ValueError('hardlink or special member')
            if name != 'receipt.json':
                entries[name] = info
    receipt = json.loads(special['receipt.json'])
    if receipt.get('schema') != 'qb.source-artifact/v1' or receipt['entries'] != entries:
        raise ValueError('receipt members')
    if digest(special['receipt.json']) != expected['receipt_sha256']:
        raise ValueError('receipt hash')
    if special['report.json'] != canonical(report) or receipt['report_sha256'] != expected['report_sha256'] or digest(special['report.json']) != expected['report_sha256']:
        raise ValueError('report binding')
    for name in entries:
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.' and entries.get(str(parent), {}).get('type') != 'directory':
                raise ValueError('non-directory ancestor')
        if entries[name]['type'] == 'symlink':
            target, visited = name, set()
            while entries.get(target, {}).get('type') == 'symlink':
                if target in visited:
                    raise ValueError('cyclic link')
                visited.add(target)
                target = posixpath.normpath(posixpath.join(posixpath.dirname(target), entries[target]['target']))
            if target not in entries:
                raise ValueError('dangling link')
    installed = {name[len('install-xacc/'):]: info['sha256'] for name, info in entries.items()
                 if name.startswith('install-xacc/') and info['type'] == 'file'}
    if len(installed) != report['installed_files'] or digest(json.dumps(installed, sort_keys=True).encode()) != report['installed_manifest_sha256']:
        raise ValueError('installed manifest binding')
    if entries['consumer-output/acz']['sha256'] != report['consumer_sha256']:
        raise ValueError('consumer binding')
    for name, stage in report['stages'].items():
        if entries['logs/' + name + '.log']['sha256'] != stage['log_sha256']:
            raise ValueError('log binding')
    return {'verified': True, 'files': len(installed), 'archive_sha256': expected['sha256']}
