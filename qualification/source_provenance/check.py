"""Read-only pre-patch source gate. No builds, acquisition, or binary-origin claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1')
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args], env=env,
                                   stderr=subprocess.DEVNULL)


def inspect(root, commit):
    root = Path(root).resolve()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('expected a full SHA-1 commit')
    if git(root, 'rev-parse', '--show-object-format').strip() != b'sha1':
        raise ValueError('unsupported object format')
    if Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve() != root:
        raise ValueError('input must be a repository root')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != commit:
        raise ValueError('HEAD differs from requested commit')
    # Include ignored files: a stale ignored build output is also undeclared input.
    if git(root, 'ls-files', '--others', '-z'):
        raise ValueError('undeclared files present (including ignored files)')
    if git(root, 'diff', '--cached', '--raw', '--no-renames', '--ignore-submodules=none', commit):
        raise ValueError('staged changes present')
    entries = []
    for raw in git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not raw:
            continue
        meta, name = raw.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        rel = os.fsdecode(name)
        path = root / rel
        # Never follow a replaced parent directory to read outside the source tree.
        if any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
            raise ValueError('symlinked parent directory: ' + rel)
        if mode == '160000' and kind == 'commit':
            if path.is_symlink():
                raise ValueError('symlinked submodule: ' + rel)
            entries.append({'path': rel, 'mode': mode, 'submodule': inspect(path, oid)})
            continue
        st = path.lstat()
        if mode == '120000' and stat.S_ISLNK(st.st_mode):
            target = os.readlink(path)
            if Path(target).is_absolute() or not path.resolve().is_relative_to(root):
                raise ValueError('source symlink escapes repository: ' + rel)
            data = os.fsencode(target)
        elif mode in ('100644', '100755') and stat.S_ISREG(st.st_mode):
            if bool(st.st_mode & 0o111) != (mode == '100755'):
                raise ValueError('executable mode mismatch: ' + rel)
            data = path.read_bytes()
        else:
            raise ValueError('unexpected source file type: ' + rel)
        observed = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if observed != oid:
            raise ValueError('working bytes differ from committed blob: ' + rel)
        entries.append({'path': rel, 'mode': mode, 'git_blob': oid,
                        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    return {'commit': commit, 'tree': git(root, 'rev-parse', commit + '^{tree}').decode().strip(),
            'entries': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('commit')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tree = inspect(args.repository, args.commit)
    payload = {'schema': 1, 'claim': 'clean_prepatch_source_only_not_binary_provenance',
               'source': tree}
    # Exclusive creation; failed checks never leave a successful-looking record.
    with args.output.open('x') as stream:
        json.dump(payload, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
