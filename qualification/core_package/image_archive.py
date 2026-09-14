"""Verify a bounded hybrid OCI/Docker save archive without extraction or execution.

Authenticates archive bytes, descriptor references and the selected Linux amd64
compressed/uncompressed layer chain. Does not inspect the layer filesystem union,
validate attestation truth/signatures, or demonstrate clean-daemon replay.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile

INDEX = 'application/vnd.oci.image.index.v1+json'
MANIFEST = 'application/vnd.oci.image.manifest.v1+json'
CONFIG = 'application/vnd.oci.image.config.v1+json'
EMPTY = 'application/vnd.oci.empty.v1+json'
LAYER = 'application/vnd.oci.image.layer.v1.tar+gzip'
TAR_LAYER = 'application/vnd.oci.image.layer.v1.tar'
STATEMENT = 'application/vnd.in-toto+json'
MAX_ARCHIVE = 2 * 1024**3
MAX_BLOB = 1024**3
MAX_JSON = 4 * 1024**2
MAX_EXPANDED_LAYER = 4 * 1024**3
MAX_EXPANDED_TOTAL = 8 * 1024**3
MAX_MEMBERS = 512
DIGEST = re.compile(r'sha256:[a-f0-9]{64}')
BLOB = re.compile(r'blobs/sha256/[a-f0-9]{64}')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'duplicate JSON key')
        out[key] = value
    return out


def parse(data):
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def hashed(stream, limit):
    h = hashlib.sha256()
    count = 0
    while True:
        chunk = stream.read(min(1024**2, limit - count + 1))
        if not chunk:
            break
        count += len(chunk)
        require(count <= limit, 'stream size limit')
        h.update(chunk)
    return h.hexdigest(), count


def preflight_headers(stream, size):
    """Reject extension headers before tarfile can allocate their payloads."""
    count = 0
    while stream.tell() < size:
        header = stream.read(512)
        require(len(header) == 512, 'partial tar header')
        if header == bytes(512):
            # tar end marker and optional block padding must all be zero.
            while True:
                rest = stream.read(1024**2)
                if not rest:
                    break
                require(not rest.strip(b'\0'), 'nonzero tar trailing data')
            stream.seek(0)
            return
        count += 1
        require(count <= MAX_MEMBERS, 'too many archive headers')
        member = tarfile.TarInfo.frombuf(header, 'utf-8', 'strict')
        require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE), 'unsupported tar header')
        require(0 <= member.size <= MAX_BLOB, 'header size limit')
        next_offset = stream.tell() + ((member.size + 511) // 512) * 512
        require(next_offset <= size, 'member outside archive')
        stream.seek(next_offset)
    raise ValueError('missing tar end marker')


def verify(archive, *, expected_sha256, expected_bytes, expected_image_id):
    require(isinstance(expected_sha256, str) and re.fullmatch('[a-f0-9]{64}', expected_sha256), 'expected archive hash')
    require(type(expected_bytes) is int and 0 < expected_bytes <= MAX_ARCHIVE, 'expected archive size')
    require(isinstance(expected_image_id, str) and DIGEST.fullmatch(expected_image_id), 'expected image identity')
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == expected_bytes, 'archive regular file/size')
        sha, size = hashed(stream, MAX_ARCHIVE)
        require((sha, size) == (expected_sha256, expected_bytes), 'archive identity mismatch')
        stream.seek(0)
        preflight_headers(stream, size)
        with tarfile.open(fileobj=stream, mode='r:') as tar:
            members = {}
            blob_names = set()
            for member in tar:
                require(len(members) < MAX_MEMBERS, 'too many archive members')
                require(member.name not in members, 'duplicate archive member')
                require(not member.pax_headers and not member.sparse, 'extended/sparse archive member')
                if member.isdir():
                    require(member.name in ('blobs', 'blobs/sha256') and member.size == 0, 'unexpected directory')
                else:
                    require(member.isreg() and member.type in (tarfile.REGTYPE, tarfile.AREGTYPE), 'non-regular archive member')
                    require(member.name in ('index.json', 'manifest.json', 'oci-layout') or BLOB.fullmatch(member.name), 'unsafe/unexpected member path')
                    require(0 <= member.size <= MAX_BLOB, 'member size limit')
                    if BLOB.fullmatch(member.name):
                        got, n = hashed(tar.extractfile(member), MAX_BLOB)
                        require(got == member.name.rsplit('/', 1)[1] and n == member.size, 'blob identity mismatch')
                        blob_names.add(member.name)
                members[member.name] = member

            def read_json(name):
                require(name in members and members[name].isreg(), 'missing JSON member')
                require(members[name].size <= MAX_JSON, 'JSON size limit')
                return parse(tar.extractfile(members[name]).read(MAX_JSON + 1))

            require(read_json('oci-layout') == {'imageLayoutVersion': '1.0.0'}, 'OCI layout version')
            index = read_json('index.json')
            require(index.get('schemaVersion') == 2 and index.get('mediaType') == INDEX, 'root index schema')
            roots = index.get('manifests')
            require(isinstance(roots, list) and len(roots) == 1 and roots[0].get('digest') == expected_image_id, 'root image identity')
            reached = set()
            documents = {}
            types = {}

            def visit(desc, depth=0):
                require(depth <= 12 and isinstance(desc, dict), 'descriptor depth/type')
                digest = desc.get('digest')
                require(isinstance(digest, str) and DIGEST.fullmatch(digest), 'descriptor digest')
                name = 'blobs/sha256/' + digest[7:]
                require(name in blob_names, 'missing referenced blob')
                require(type(desc.get('size')) is int and desc['size'] == members[name].size, 'descriptor size')
                media = desc.get('mediaType')
                require(media in (INDEX, MANIFEST, CONFIG, EMPTY, LAYER, TAR_LAYER, STATEMENT), 'unsupported media type')
                require(digest not in types or types[digest] == media, 'conflicting media types')
                types[digest] = media
                require(not desc.get('urls'), 'external descriptor URLs unsupported')
                if 'data' in desc:
                    require(isinstance(desc['data'], str) and len(desc['data']) <= MAX_JSON * 2, 'inline descriptor limit')
                    data = base64.b64decode(desc['data'], validate=True)
                    require(len(data) == desc['size'] and hashlib.sha256(data).hexdigest() == digest[7:], 'inline descriptor identity')
                if name in reached:
                    return
                reached.add(name)
                if media in (INDEX, MANIFEST, CONFIG, EMPTY, STATEMENT):
                    doc = read_json(name)
                    require(isinstance(doc, dict), 'descriptor JSON object')
                    documents[digest] = doc
                    if media in (INDEX, MANIFEST):
                        require(doc.get('schemaVersion') == 2 and doc.get('mediaType') == media, 'descriptor schema')
                        if media == INDEX:
                            refs = doc.get('manifests')
                            require(isinstance(refs, list) and 0 < len(refs) <= MAX_MEMBERS, 'index manifests')
                        else:
                            require(isinstance(doc.get('layers'), list) and len(doc['layers']) <= MAX_MEMBERS, 'manifest layers')
                            refs = [doc.get('config')] + doc['layers']
                            if 'subject' in doc:
                                refs.append(doc['subject'])
                        for ref in refs:
                            visit(ref, depth + 1)

            visit(roots[0])
            require(reached == blob_names, 'unreferenced blobs')
            root = documents[expected_image_id]
            require(types[expected_image_id] == INDEX, 'expected image must be saved OCI index')
            choices = [d for d in root['manifests'] if d.get('platform') == {'architecture': 'amd64', 'os': 'linux'} and d.get('mediaType') == MANIFEST]
            require(len(choices) == 1, 'exactly one linux amd64 image required')
            selected = choices[0]
            manifest = documents[selected['digest']]
            require('artifactType' not in manifest and manifest['config']['mediaType'] == CONFIG, 'selected image config')
            config_id = manifest['config']['digest']
            config = documents[config_id]
            require(config.get('architecture') == 'amd64' and config.get('os') == 'linux', 'config platform')
            rootfs = config.get('rootfs', {})
            require(rootfs.get('type') == 'layers' and isinstance(rootfs.get('diff_ids'), list), 'config rootfs')
            layers = manifest['layers']
            require(0 < len(layers) == len(rootfs['diff_ids']) <= 128, 'layer chain length')
            docker = read_json('manifest.json')
            require(isinstance(docker, list) and len(docker) == 1, 'Docker manifest cardinality')
            require(docker[0].get('Config') == 'blobs/sha256/' + config_id[7:] and docker[0].get('Layers') == ['blobs/sha256/' + d['digest'][7:] for d in layers], 'Docker/OCI manifest mismatch')
            chain = []
            total = 0
            for layer, diff_id in zip(layers, rootfs['diff_ids']):
                require(isinstance(diff_id, str) and DIGEST.fullmatch(diff_id), 'config diff id')
                require(layer['mediaType'] in (LAYER, TAR_LAYER), 'selected layer media type')
                source = tar.extractfile(members['blobs/sha256/' + layer['digest'][7:]])
                with source:
                    if layer['mediaType'] == LAYER:
                        with gzip.GzipFile(fileobj=source) as expanded:
                            digest, n = hashed(expanded, min(MAX_EXPANDED_LAYER, MAX_EXPANDED_TOTAL - total))
                    else:
                        digest, n = hashed(source, min(MAX_EXPANDED_LAYER, MAX_EXPANDED_TOTAL - total))
                total += n
                require('sha256:' + digest == diff_id, 'uncompressed layer identity mismatch')
                chain.append({'digest': layer['digest'], 'bytes': layer['size'], 'diff_id': diff_id, 'expanded_bytes': n})
        after = os.fstat(stream.fileno())
        require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'archive changed during verification')
    return {'schema': 'qb.qpp-image-archive-verification/v1', 'archive_sha256': sha,
            'archive_bytes': size, 'image_index_digest': expected_image_id,
            'amd64_manifest_digest': selected['digest'], 'config_digest': config_id,
            'platform': 'linux/amd64', 'blob_count': len(blob_names), 'layers': chain,
            'references_complete': True, 'layer_diff_ids_verified': True,
            'filesystem_union_verified': False, 'attestation_claims_verified': False,
            'clean_daemon_replay_verified': False, 'runtime_qualified': False,
            'redistribution_cleared': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--expected-bytes', required=True, type=int)
    p.add_argument('--expected-image-id', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = vars(p.parse_args())
    output = args.pop('output')
    require(not output.exists(), 'output already exists')
    result = verify(**args)
    with output.open('x') as f:
        f.write(json.dumps(result, indent=2) + '\n')
