"""Bounded Core success/failure receipts; inspect tar without extracting paths."""
from contextlib import nullcontext
import hashlib
import json
import posixpath
import os
import re
import stat
import tarfile
from pathlib import Path, PurePosixPath

MAX_BYTES = 1024 * 1024 * 1024
MAX_MEMBERS = 50000
SUCCESS_ROOTS = {'install-core', 'install-xacc', 'antlr', 'consumer', 'consumer-output', 'logs'}
PLUGINS = {'qb_gateset_transpiler', 'qb_qobj_compiler', 'algorithm_ae', 'algorithm_es',
           'aws_braket', 'circuits', 'sparse_simulator', 'uccsd', 'vqe'}


def normalize(base):
    """Only change known Core links on the disposable install derivative.

    Call before installed-only consumer replay. Nothing is copied or installed.
    All changes are validated before the first replacement. A filesystem error
    mid-application may leave a partial derivative: discard it, never promote it.
    """
    base = Path(base)
    core = base / 'install-core'
    plugins = base / 'install-xacc/plugins'
    for path in (base, core, core / 'lib', base / 'install-xacc', plugins):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('normalization root')
    changes = []
    for path in sorted(plugins.iterdir()):
        if not path.is_symlink():
            continue
        old = str(path.readlink())
        if not old.startswith('/'):
            continue
        match = re.fullmatch(r'/work/install-core/lib/lib([a-zA-Z0-9_]+)\.so(?:\.[0-9]+)*', old)
        if not match or match.group(1) not in PLUGINS or path.name != PurePosixPath(old).name:
            raise ValueError('unapproved absolute plugin link')
        target = core / 'lib' / path.name
        if not target.is_file() or not target.resolve().is_relative_to((core / 'lib').resolve()):
            raise ValueError('plugin target missing or escaping')
        relative = '../../install-core/lib/' + path.name
        changes.append({'path': 'install-xacc/plugins/' + path.name, 'before': old, 'after': relative,
                        'target_sha256': digest(target.read_bytes())})
    for item in changes:
        path = base / item['path']
        # Atomic replacement, with a private unique temporary link next to it.
        import uuid
        temporary = path.parent / ('.normalize-' + uuid.uuid4().hex)
        temporary.symlink_to(item['after'])
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {'schema': 'qb.core-plugin-normalization/v1', 'changes': changes,
            'installed_consumer_replayed': False}


def check_scope(entries, report):
    success = report.get('native_passed') is True
    if success and report.get('error'):
        raise ValueError('conflicting report')
    roots = {name.split('/')[0] for name in entries} - {'report.json'}
    if roots != (SUCCESS_ROOTS if success else {'logs'}):
        raise ValueError('output scope')
    stages = report.get('stages', {})
    if not isinstance(stages, dict) or any(not re.fullmatch('[a-z][a-z0-9-]{0,63}', name) for name in stages):
        raise ValueError('stage names')
    logs = {name for name in entries if name.startswith('logs/')}
    if logs != {'logs/' + name + '.log' for name in stages}:
        raise ValueError('unlisted log or missing stage log')
    for name, stage in stages.items():
        info = entries['logs/' + name + '.log']
        if info.get('type') != 'file' or info['sha256'] != stage.get('log_sha256'):
            raise ValueError('log binding')
    if success:
        if {name for name in entries if name.startswith('antlr/')} != {'antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl'}:
            raise ValueError('ANTLR output scope')
        if entries['antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl']['type'] != 'file':
            raise ValueError('ANTLR file type')
        selected = {name: info['sha256'] for name, info in entries.items()
                    if name.split('/')[0] in {'consumer', 'consumer-output', 'antlr'} and info['type'] == 'file'}
        if selected != report.get('retained_files') or not any(n.startswith('consumer/') for n in selected) or not any(n.startswith('consumer-output/') for n in selected):
            raise ValueError('executed output identity binding')
        normalization = report.get('plugin_normalization', {})
        if normalization.get('schema') != 'qb.core-plugin-normalization/v1':
            raise ValueError('normalization receipt missing')
        # Record alone never proves replay ordering: native stage checker must
        # independently enforce normalize before consumer build/run.
        for change in normalization.get('changes', []):
            name = change['path']
            match = re.fullmatch(r'install-xacc/plugins/lib([a-zA-Z0-9_]+)\.so(?:\.[0-9]+)*', name)
            basename = PurePosixPath(name).name
            if (not match or match.group(1) not in PLUGINS
                    or change['before'] != '/work/install-core/lib/' + basename
                    or change['after'] != '../../install-core/lib/' + basename):
                raise ValueError('unapproved normalization receipt')
            info = entries.get(name, {})
            if info.get('type') != 'symlink' or info.get('target') != change['after']:
                raise ValueError('normalization output mismatch')
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), change['after']))
            if entries.get(target, {}).get('sha256') != change['target_sha256']:
                raise ValueError('normalized target binding')


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


def check_links(entries):
    for name, entry in entries.items():
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.' and entries.get(str(parent), {}).get('type') != 'directory':
                raise ValueError('non-directory ancestor')
        if entry['type'] == 'symlink':
            target, visited = name, set()
            while entries.get(target, {}).get('type') == 'symlink':
                if target in visited:
                    raise ValueError('cyclic link')
                visited.add(target)
                target = posixpath.normpath(posixpath.join(posixpath.dirname(target), entries[target]['target']))
            if target not in entries:
                raise ValueError('dangling link')


def pack(output, report, roots):
    """Called outside workloads; only explicitly named public-output roots enter tar."""
    required = SUCCESS_ROOTS if report.get('native_passed') is True else {'logs'}
    if set(roots) != required:
        raise ValueError('output root scope')
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
    check_scope(entries, report)
    check_links(entries)
    raw_report = canonical(report)
    entries['report.json'] = {'type': 'file', 'mode': 0o644, 'size': len(raw_report), 'sha256': digest(raw_report)}
    receipt = {'schema': 'qb.core-output/v1', 'report_sha256': digest(raw_report), 'entries': entries}
    import io
    with tarfile.open(output, 'x:gz', dereference=False) as archive:
        for name, path in files.items():
            member = archive.gettarinfo(str(path), arcname=name)
            # Do not let tarfile coalesce repeated inodes into hardlinks.
            if member.islnk():
                member.type, member.linkname, member.size = tarfile.REGTYPE, '', path.stat().st_size
            with path.open('rb') if member.isfile() else nullcontext(None) as stream:
                archive.addfile(member, stream)
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
    if receipt.get('schema') != 'qb.core-output/v1' or receipt['entries'] != entries:
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
    check_scope(entries, report)
    return {'verified': True, 'native_passed': report.get('native_passed') is True,
            'archive_sha256': expected['sha256'], 'entries': len(entries)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    normal = commands.add_parser('normalize')
    normal.add_argument('base', type=Path)
    normal.add_argument('receipt', type=Path)
    build = commands.add_parser('pack')
    build.add_argument('report', type=Path)
    build.add_argument('roots', type=Path, help='JSON mapping allowed root names to explicit directories')
    build.add_argument('output', type=Path)
    build.add_argument('identity', type=Path)
    check = commands.add_parser('verify')
    check.add_argument('archive', type=Path)
    check.add_argument('identity', type=Path)
    check.add_argument('report', type=Path)
    args = parser.parse_args()
    if args.command == 'normalize':
        if args.receipt.exists():
            raise ValueError('normalization receipt must be new')
        result = normalize(args.base)
        with args.receipt.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    elif args.command == 'pack':
        if args.output.exists() or args.identity.exists():
            raise ValueError('output must be new')
        result = pack(args.output, json.loads(args.report.read_text()), json.loads(args.roots.read_text()))
        with args.identity.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    else:
        result = verify(args.archive, json.loads(args.identity.read_text()), json.loads(args.report.read_text()))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
