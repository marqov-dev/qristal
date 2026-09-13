"""Stage a verified XACC archive into a new directory; never execute its contents."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('retained_archive', HERE.parent / 'source_artifact/archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def verify_tree(root, entries):
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')}
    if actual != set(entries):
        raise ValueError('staged inventory mismatch')
    for name, entry in entries.items():
        path = root / name
        info = path.lstat()
        if stat.S_IMODE(info.st_mode) != entry['mode']:
            raise ValueError('staged mode mismatch')
        if entry['type'] == 'file':
            if not stat.S_ISREG(info.st_mode) or info.st_size != entry['size'] or archive.digest(path.read_bytes()) != entry['sha256']:
                raise ValueError('staged file mismatch')
        elif entry['type'] == 'directory':
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('staged directory mismatch')
        elif not stat.S_ISLNK(info.st_mode) or os.readlink(path) != entry['target']:
            raise ValueError('staged link mismatch')


def prepare(source, recovered, output, *, archive_only=False):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('output must be new')
    output = output.parent.resolve(strict=True) / output.name
    envelope = recovered.get('result', recovered)
    identity = envelope['output_artifact']
    report = {k: v for k, v in envelope.items() if k != 'output_artifact'}
    if report.get('native_passed') is not True:
        raise ValueError('native success required')
    # A private snapshot binds verification and extraction to the same bytes.
    # No tar extraction API is used; links are created only after regular files.
    with tempfile.TemporaryDirectory(prefix='.xacc-input-', dir=output.parent) as temporary:
        work = Path(temporary)
        snapshot = work / 'archive.tar.gz'
        with source.open('rb') as src, snapshot.open('xb') as dst:
            copied = 0
            while data := src.read(1024 * 1024):
                copied += len(data)
                if copied > archive.MAX_BYTES:
                    raise ValueError('archive byte bound')
                dst.write(data)
        checked = archive.verify(snapshot, identity, report)
        with tarfile.open(snapshot, 'r:gz') as tar:
            receipt = json.load(tar.extractfile('receipt.json'))
        entries = receipt['entries']
        staged = {'schema': 'qb.installed-input/v1', 'archive': identity,
                  'verified': checked['verified'], 'installed_files': checked['files'],
                  'required_guest_prefix': '/work/install-xacc', 'entries': entries,
                  'materialization': 'archive-only' if archive_only else 'tree',
                  'executed': False, 'relocatable': False}
        if archive_only:
            output.mkdir(mode=0o700)
            snapshot.rename(output / 'archive.tar.gz')
            (output / 'recovered.json').write_text(json.dumps(envelope, sort_keys=True) + '\n')
            (output / 'staging.json').write_text(json.dumps(staged, indent=2, sort_keys=True) + '\n')
            return {k: v for k, v in staged.items() if k != 'entries'}
        probe = work / 'CaseProbe'; probe.touch()
        insensitive = (work / 'caseprobe').exists(); probe.unlink()
        if insensitive and len({name.casefold() for name in entries}) != len(entries):
            raise ValueError('archive requires a case-sensitive filesystem; use archive-only transport')
        tree = work / 'tree'; tree.mkdir(mode=0o700)
        with tarfile.open(snapshot, 'r:gz') as tar:
            for name, entry in sorted(entries.items(), key=lambda pair: (pair[0].count('/'), pair[0])):
                path = tree / name
                if entry['type'] == 'directory':
                    path.mkdir(mode=0o700)
                elif entry['type'] == 'file':
                    with tar.extractfile(name) as src, path.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
                    path.chmod(entry['mode'])
            for name, entry in entries.items():
                if entry['type'] == 'symlink':
                    path = tree / name
                    path.symlink_to(entry['target'])
                    if stat.S_IMODE(path.lstat().st_mode) != entry['mode']:
                        if not hasattr(os, 'lchmod'):
                            raise ValueError('host cannot preserve symlink mode')
                        os.lchmod(path, entry['mode'])
            for name, entry in sorted(entries.items(), reverse=True):
                if entry['type'] == 'directory':
                    (tree / name).chmod(entry['mode'])
        verify_tree(tree, entries)
        (work / 'staging.json').write_text(json.dumps(staged, indent=2, sort_keys=True) + '\n')
        # mkdir(exist_ok=False) prevents replacing a concurrently created target.
        output.mkdir(mode=0o700)
        tree.rename(output / 'tree')
        (work / 'staging.json').rename(output / 'staging.json')
        return {k: v for k, v in staged.items() if k != 'entries'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('recovered', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--archive-only', action='store_true', help='verify and retain transport inputs without unpacking')
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, json.loads(args.recovered.read_text()), args.output, archive_only=args.archive_only), indent=2))
