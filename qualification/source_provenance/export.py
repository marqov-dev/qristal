"""Export locked Git objects, never reused working bytes, to a new source directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from check import git


def export_tree(repository, commit, destination):
    repository, destination = Path(repository).resolve(), Path(destination)
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('full commit required')
    if git(repository, 'rev-parse', '--show-object-format').strip() != b'sha1':
        raise ValueError('SHA-1 repository required')
    # Require a commit object, not a tree/blob or abbreviated revision.
    if git(repository, 'cat-file', '-t', commit).strip() != b'commit':
        raise ValueError('commit object required')
    destination.mkdir()  # Never merge with existing output, even if empty.
    entries = []
    for raw in git(repository, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not raw:
            continue
        meta, raw_name = raw.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        name = os.fsdecode(raw_name)
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
            raise ValueError('unsafe Git source path')
        target = destination / name
        # Git trees cannot contain a blob as an ancestor; reject any unexpected
        # filesystem link as well. Only this exporter should write the output.
        if any(p.is_symlink() for p in target.parents if p != destination and destination in p.parents):
            raise ValueError('symlinked output parent')
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == '160000' and kind == 'commit':
            child = repository / name
            if child.is_symlink() or child.resolve() != child:
                raise ValueError('symlinked source submodule')
            if Path(os.fsdecode(git(child, 'rev-parse', '--show-toplevel')).strip()).resolve() != child:
                raise ValueError('submodule object repository missing')
            entries.append({'path': name, 'mode': mode,
                            'submodule': export_tree(child, oid, target)})
            continue
        if kind != 'blob' or mode not in ('100644', '100755', '120000'):
            raise ValueError('unsupported Git entry')
        data = git(repository, 'cat-file', 'blob', oid)
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != oid:
            raise ValueError('Git object bytes mismatch')
        if mode == '120000':
            link = os.fsdecode(data)
            if Path(link).is_absolute() or not (target.parent / link).resolve().is_relative_to(destination.resolve()):
                raise ValueError('escaping source symlink')
            target.symlink_to(link)
        else:
            with target.open('xb') as out:
                out.write(data)
            target.chmod(0o755 if mode == '100755' else 0o644)
        entries.append({'path': name, 'mode': mode, 'git_blob': oid,
                        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    return {'commit': commit, 'tree': git(repository, 'rev-parse', commit + '^{tree}').decode().strip(),
            'entries': entries}


def verify_tree(root, receipt):
    """Check exported bytes against their receipt, including unexpected files."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('source root must be a real directory')
    root = root.resolve()
    expected = set()
    for entry in receipt['entries']:
        name = entry['path']
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
            raise ValueError('unsafe receipt path')
        path = root / name
        if any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
            raise ValueError('symlinked source parent')
        if 'submodule' in entry:
            if path.is_symlink():
                raise ValueError('symlinked submodule')
            verify_tree(path, entry['submodule'])
            expected.update(str(Path(name) / p.relative_to(path)) for p in path.rglob('*') if not p.is_dir() or p.is_symlink())
        else:
            expected.add(name)
            if entry['mode'] == '120000':
                if not path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError('source symlink mismatch')
                data = os.fsencode(os.readlink(path))
            else:
                if path.is_symlink() or not path.is_file():
                    raise ValueError('source file type mismatch')
                if bool(path.stat().st_mode & 0o111) != (entry['mode'] == '100755'):
                    raise ValueError('source executable mode mismatch')
                data = path.read_bytes()
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('source bytes mismatch')
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if not p.is_dir() or p.is_symlink()}
    if actual != expected:
        raise ValueError('undeclared or missing source files')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('commit')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists() or args.receipt.resolve().is_relative_to(args.destination.resolve()):
        raise ValueError('receipt must be a new file outside exported source')
    source = export_tree(args.repository, args.commit, args.destination)
    verify_tree(args.destination, source)
    with args.receipt.open('x') as output:
        json.dump({'schema': 1, 'claim': 'exported_git_objects_only_not_binary_provenance',
                   'source': source}, output, indent=2)
        output.write('\n')


if __name__ == '__main__':
    main()
