"""Prepare a fresh patched XACC input archive from retained clean-source receipts."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PROVENANCE = HERE.parent / 'source_provenance'
import sys
sys.path.insert(0, str(PROVENANCE))
spec = importlib.util.spec_from_file_location('source_export', PROVENANCE / 'export.py')
source_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_export)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        name = str(path.relative_to(root))
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('escaping input symlink')
            result[name] = {'link': str(path.readlink())}
        elif path.is_file():
            if not path.stat().st_mode & 0o004:
                raise ValueError('input not readable by runtime user')
            result[name] = {'sha256': sha(path), 'mode': path.stat().st_mode & 0o777}
        elif path.is_dir():
            if path.stat().st_mode & 0o005 != 0o005:
                raise ValueError('input directory not traversable')
            result[name] = {'directory': path.stat().st_mode & 0o777}
        else:
            raise ValueError('special input file')
    return result


def prepare(inputs, output):
    if output.resolve().is_relative_to(inputs.resolve()):
        raise ValueError('output inside inputs')
    evidence = HERE.parent / 'evidence/2026-09-13-pristine-sources'
    summary = json.loads((evidence / 'summary.json').read_text())
    for item in summary['components']:
        stored = evidence / item['receipt']
        if sha(stored) != item['stored_sha256']:
            raise ValueError('receipt stored identity')
        raw = gzip.decompress(stored.read_bytes())
        if hashlib.sha256(raw).hexdigest() != item['receipt_sha256']:
            raise ValueError('receipt identity')
        source_export.verify_tree(inputs / item['component'], json.loads(raw)['source'])
    for item in summary['materials']:
        path = inputs / item['path'] if item['path'].startswith('archives/') else inputs / 'qualification-inputs' / item['path']
        if sha(path) != item['sha256']:
            raise ValueError('material identity')
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'work'
    work.mkdir(mode=0o755)
    work.chmod(0o755)
    for name in ('xacc', 'googletest'):
        shutil.copytree(inputs / name, work / name, symlinks=True)
    (work / 'archives').mkdir()
    for item in summary['materials']:
        if item['path'].startswith('archives/'):
            shutil.copyfile(inputs / item['path'], work / item['path'])
            if sha(work / item['path']) != item['sha256']:
                raise ValueError('copied archive identity')
    for item in summary['components']:
        raw = gzip.decompress((evidence / item['receipt']).read_bytes())
        source_export.verify_tree(work / item['component'], json.loads(raw)['source'])
    transformations = []
    for name, target in [('xacc-cpu.patch', work / 'xacc'), ('cppmicroservices.patch', work / 'xacc/tpls/cppmicroservices')]:
        patch = (inputs / 'qualification-inputs' / name).resolve()
        subprocess.run(['git', 'apply', '--check', str(patch)], cwd=target, check=True, capture_output=True)
        subprocess.run(['git', 'apply', str(patch)], cwd=target, check=True, capture_output=True)
        transformations.append({'patch': name, 'sha256': sha(patch), 'target': str(target.relative_to(work))})
    patch = HERE / 'xacc-build-output.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=work / 'xacc', check=True, capture_output=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=work / 'xacc', check=True, capture_output=True)
    transformations.append({'patch': patch.name, 'sha256': sha(patch), 'target': 'xacc'})
    shutil.copyfile(inputs / 'qualification-inputs/acz_qpp_smoke.cpp', work / 'acz_qpp_smoke.cpp')
    shutil.copyfile(inputs / 'qualification-inputs/install-toolchain.sh', work / 'install-toolchain.sh')
    shutil.copyfile(HERE / 'guest.py', work / 'guest.py')
    base = json.loads((inputs / 'qualification-inputs/source-lock.json').read_text())['ubuntu_base']
    (work / 'Dockerfile').write_text('FROM ' + base + '\nCOPY install-toolchain.sh /install-toolchain.sh\nRUN sh /install-toolchain.sh\n')
    record = {'schema': 'qb.source-build-input/v1', 'source_summary_sha256': sha(evidence / 'summary.json'),
              'transformations': transformations, 'files': inventory(work), 'base': base}
    (work / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    with tarfile.open(output / 'cpu.tar.gz', 'w:gz', dereference=False) as archive:
        for path in sorted(work.iterdir()):
            archive.add(path, arcname=path.name)
    (output / 'archive.json').write_text(json.dumps({'sha256': sha(output / 'cpu.tar.gz'), 'bytes': (output / 'cpu.tar.gz').stat().st_size}, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    prepare(args.inputs, args.output)
