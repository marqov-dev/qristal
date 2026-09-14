"""Prepare and verify a notice-only image overlay; no build, load or execution.

Private snapshots bind verification to supplied archive and context hashes. Layer
inspection is limited to the single added layer; baseline filesystem union safety
and redistribution clearance are not established here.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent

def load(name):
    spec = importlib.util.spec_from_file_location('overlay_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

ARCHIVE = load('image_archive')
STAGE = load('stage')
BASE_ID = 'sha256:8d8a81d995325ae9c452dca2698442b02c735cc6eae9d98ea78a38532a5a8266'
BASE_SHA = '139d7b3e5bc463f2067bfd9a5beda4a59326a996d7fd8d95ea9e3f06c332a4eb'
BASE_BYTES = 514063872
INDEX_SHA = '3c806d11a02c3ada3e19fed98ac9cbca65faa97378e543af354e80a156c43a49'
PREFIX = 'opt/qristal/attribution'
MAX_FILE = 4 * 1024**2
MAX_TOTAL = 64 * 1024**2
BASE_RESOLUTION = 'local-tag-requires-post-build-archive-verification'
DOCKERFILE = ('FROM qristal-qpp-local:20260914\n'
              'COPY --chown=0:0 attribution/ /opt/qristal/attribution/\n')


def require(ok, message):
    if not ok: raise ValueError(message)


def safe(name):
    require(isinstance(name, str) and bool(name) and '\\' not in name and '\x00' not in name, 'unsafe path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and str(p) == name and name != '.', 'unsafe path')
    require(not any(part.startswith('.wh.') for part in p.parts), 'whiteout path')
    return name


def source_path(root, name):
    name = safe(name); p = root / name
    require(not root.is_symlink() and not any(x.is_symlink() for x in (p, *p.parents) if x == root or root in x.parents), 'symlink source path')
    return p


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def copy_file(root, name, destination, expected):
    require(type(expected.get('bytes')) is int and 0 <= expected['bytes'] <= MAX_FILE, 'file bound')
    require(isinstance(expected.get('sha256'), str) and re.fullmatch('[a-f0-9]{64}', expected['sha256']), 'file digest')
    destination.parent.mkdir(parents=True, exist_ok=True)
    STAGE.snapshot(source_path(root, name), destination, MAX_FILE, expected)
    destination.chmod(0o644)


def snapshot_payload(payload, destination, expected_index_sha256):
    require(re.fullmatch('[a-f0-9]{64}', expected_index_sha256), 'index digest')
    destination.mkdir()
    index_path = destination / 'ATTRIBUTION_INDEX.json'
    got = STAGE.snapshot(source_path(payload, 'ATTRIBUTION_INDEX.json'), index_path, MAX_FILE)
    require(got['sha256'] == expected_index_sha256, 'attribution index identity')
    index_path.chmod(0o644)
    index = ARCHIVE.parse(index_path.read_bytes())
    require(index.get('schema') == 'qb.attribution-payload/v1' and index.get('coverage_complete') is False and index.get('legal_conclusion') is None, 'attribution scope/schema')
    entries = index.get('entries'); files = index.get('files')
    require(isinstance(entries, dict) and isinstance(files, dict) and 0 < len(files) <= 4096, 'attribution inventory')
    require(set(files) == set(entries) | {'README.txt'} and 'README.txt' not in entries, 'complete attribution file set')
    require(index.get('notice_count') == len(entries), 'notice count')
    for name, entry in entries.items():
        require(files[name] == {k: entry[k] for k in ('bytes', 'sha256')}, 'notice inventory mismatch')
    expected = dict(files, **{'ATTRIBUTION_INDEX.json': got})
    require(sum(e['bytes'] for e in expected.values()) <= MAX_TOTAL, 'payload total bound')
    observed = set()
    for directory, dirs, names in os.walk(payload, followlinks=False):
        for name in dirs:
            require(not (Path(directory) / name).is_symlink(), 'payload directory symlink')
        for name in names:
            relative = (Path(directory) / name).relative_to(payload).as_posix()
            safe(relative); observed.add(relative)
    require(observed == set(expected), 'unexpected/missing payload files')
    for name, entry in files.items():
        copy_file(payload, name, destination / safe(name), entry)
    for directory, dirs, _ in os.walk(destination):
        Path(directory).chmod(0o755)
    return expected


def prepare(payload, output, *, expected_index_sha256=INDEX_SHA):
    payload, output = Path(payload), Path(output)
    require(not output.exists() and not output.is_symlink(), 'new output required')
    with tempfile.TemporaryDirectory(prefix='.notice-context-', dir=output.parent) as tmp:
        context = Path(tmp) / 'context'; context.mkdir()
        files = snapshot_payload(payload, context / 'attribution', expected_index_sha256)
        (context / 'Dockerfile').write_text(DOCKERFILE)
        (context / 'Dockerfile').chmod(0o644)
        receipt = {'schema': 'qb.notice-overlay-context/v1', 'base_image_id': BASE_ID,
                   'base_resolution': BASE_RESOLUTION,
                   'attribution_index_sha256': expected_index_sha256, 'files': files,
                   'dockerfile': identity(context / 'Dockerfile'), 'built': False,
                   'coverage_complete': False, 'redistribution_cleared': False}
        (context / 'context.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        output.mkdir()
        try: os.replace(context, output)
        except Exception: output.rmdir(); raise
        return dict(receipt, context_sha256=identity(output / 'context.json')['sha256'])


def snapshot_context(context, private, expected_context_sha256):
    private.mkdir()
    receipt_path = private / 'context.json'
    got = STAGE.snapshot(source_path(context, 'context.json'), receipt_path, MAX_FILE)
    require(got['sha256'] == expected_context_sha256, 'context identity')
    receipt = ARCHIVE.parse(receipt_path.read_bytes())
    require(receipt.get('schema') == 'qb.notice-overlay-context/v1' and receipt.get('base_image_id') == BASE_ID and receipt.get('base_resolution') == BASE_RESOLUTION, 'context schema/base')
    require(receipt.get('coverage_complete') is False and receipt.get('redistribution_cleared') is False, 'context scope')
    files = snapshot_payload(context / 'attribution', private / 'attribution', receipt['attribution_index_sha256'])
    require(files == receipt['files'], 'context payload inventory mismatch')
    copy_file(context, 'Dockerfile', private / 'Dockerfile', receipt['dockerfile'])
    require((private / 'Dockerfile').read_text() == DOCKERFILE, 'notice-only Dockerfile')
    return receipt


def config(archive, digest):
    with tarfile.open(archive, 'r:') as tar:
        return ARCHIVE.parse(tar.extractfile('blobs/sha256/' + digest[7:]).read(ARCHIVE.MAX_JSON + 1))


def check_configs(old, new):
    require(old.get('architecture') == new.get('architecture') == 'amd64' and old.get('os') == new.get('os') == 'linux', 'overlay platform changed')
    require(old.get('config') == new.get('config') and isinstance(old.get('config'), dict), 'runtime config changed')
    # Platform-related optional fields must also remain exactly preserved.
    for field in ('variant', 'os.version', 'os.features'):
        require(old.get(field) == new.get(field), 'optional platform changed')
    before = old['rootfs']['diff_ids']; after = new['rootfs']['diff_ids']
    require(old['rootfs']['type'] == new['rootfs']['type'] == 'layers' and len(before) == 10 and len(after) == 11 and after[:-1] == before, 'base layer prefix changed')


def inspect_added_layer(layer_path, expected):
    files = {PREFIX + '/' + safe(name): entry for name, entry in expected.items()}
    directories = {'opt', 'opt/qristal', PREFIX}
    for name in files:
        directories.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.')
    seen = set(); found = set()
    with tarfile.open(layer_path, 'r|') as tar:
        for member in tar:
            name = safe(member.name.rstrip('/'))
            require(name not in seen and len(seen) < 8192, 'duplicate/excess layer members')
            seen.add(name)
            require(not member.sparse and set(member.pax_headers) <= {'path', 'mtime', 'atime', 'ctime'}, 'layer extended metadata')
            require(member.uid == 0 and member.gid == 0 and not member.linkname, 'layer ownership/link metadata')
            if member.isdir():
                require(name in directories and member.mode == 0o755 and member.size == 0, 'unexpected directory metadata')
                continue
            require(member.isreg() and member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and name in files, 'unexpected layer file/type')
            entry = files[name]
            require(member.mode == 0o644 and member.size == entry['bytes'] and member.size <= MAX_FILE, 'notice metadata')
            with tar.extractfile(member) as stream:
                digest, size = ARCHIVE.hashed(stream, MAX_FILE)
            require({'bytes': size, 'sha256': digest} == entry, 'notice content changed')
            found.add(name)
    require(found == set(files), 'missing attribution layer files')
    return {'files_verified': len(found), 'directories_observed': len(seen) - len(found)}


def verify(context, old_archive, new_archive, *, expected_context_sha256,
           new_sha256, new_bytes, new_image_id):
    with tempfile.TemporaryDirectory(prefix='notice-overlay-verify-') as tmp:
        private = Path(tmp)
        receipt = snapshot_context(Path(context), private / 'context', expected_context_sha256)
        old, new = private / 'old.tar', private / 'new.tar'
        STAGE.snapshot(Path(old_archive), old, ARCHIVE.MAX_ARCHIVE, {'bytes': BASE_BYTES, 'sha256': BASE_SHA})
        STAGE.snapshot(Path(new_archive), new, ARCHIVE.MAX_ARCHIVE, {'bytes': new_bytes, 'sha256': new_sha256})
        old_proof = ARCHIVE.verify(old, expected_sha256=BASE_SHA, expected_bytes=BASE_BYTES, expected_image_id=BASE_ID)
        new_proof = ARCHIVE.verify(new, expected_sha256=new_sha256, expected_bytes=new_bytes, expected_image_id=new_image_id)
        check_configs(config(old, old_proof['config_digest']), config(new, new_proof['config_digest']))
        # Preserve both uncompressed diff IDs and exact compressed base blobs.
        require(new_proof['layers'][:-1] == old_proof['layers'], 'compressed base layer chain changed')
        added = new_proof['layers'][-1]
        layer_path = private / 'added-layer.tar'
        with tarfile.open(new, 'r:') as tar, tar.extractfile('blobs/sha256/' + added['digest'][7:]) as raw:
            with gzip.GzipFile(fileobj=raw) as expanded, layer_path.open('xb') as target:
                h = hashlib.sha256(); size = 0
                while chunk := expanded.read(1024**2):
                    size += len(chunk); require(size <= MAX_TOTAL, 'added layer expanded bound')
                    h.update(chunk); target.write(chunk)
        require('sha256:' + h.hexdigest() == added['diff_id'] and size == added['expanded_bytes'], 'added layer identity')
        layer_result = inspect_added_layer(layer_path, receipt['files'])
        return {'schema': 'qb.notice-overlay-verification/v1', 'context_sha256': expected_context_sha256,
                'attribution_index_sha256': receipt['attribution_index_sha256'],
                'base_archive': old_proof, 'overlay_archive': new_proof, 'added_layer': layer_result,
                'base_resolution': 'local-tag-verified-by-preserved-archive-layer-chain-and-config',
                'runtime_config_preserved': True, 'base_layers_preserved': True,
                'added_layer_only_attribution': True, 'baseline_filesystem_union_verified': False,
                'clean_daemon_replay_verified': False, 'runtime_qualified': False,
                'coverage_complete': False, 'redistribution_cleared': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('payload', type=Path); prep.add_argument('output', type=Path)
    prep.add_argument('--expected-index-sha256', default=INDEX_SHA)
    check = sub.add_parser('verify')
    for name in ('context', 'old_archive', 'new_archive'): check.add_argument(name, type=Path)
    for name in ('expected-context-sha256', 'new-sha256', 'new-image-id'): check.add_argument('--' + name, required=True)
    check.add_argument('--new-bytes', type=int, required=True); check.add_argument('--output', type=Path, required=True)
    args = vars(p.parse_args()); command = args.pop('command')
    if command == 'prepare':
        print(json.dumps(prepare(**args), sort_keys=True))
    else:
        output = args.pop('output'); require(not output.exists(), 'new receipt output required')
        result = verify(**args)
        with output.open('x') as f: f.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'added_layer_only_attribution': True, 'redistribution_cleared': False}))
