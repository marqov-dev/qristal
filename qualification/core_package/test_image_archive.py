import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import image_archive as subject


def encoded(data):
    return json.dumps(data, sort_keys=True).encode()


class ArchiveTests(unittest.TestCase):
    def fixture(self, *, wrong_diff=False, missing=False, wrong_platform=False, wrong_size=False, docker_mismatch=False, extra=False):
        blobs = {}

        def blob(data, media):
            if not isinstance(data, bytes):
                data = encoded(data)
            digest = 'sha256:' + hashlib.sha256(data).hexdigest()
            blobs['blobs/sha256/' + digest[7:]] = data
            return {'digest': digest, 'size': len(data), 'mediaType': media}

        layer_bytes = bytes(1024)
        layer = blob(gzip.compress(layer_bytes, mtime=0), subject.LAYER)
        config = blob({'architecture': 'arm64' if wrong_platform else 'amd64', 'os': 'linux',
                       'rootfs': {'type': 'layers', 'diff_ids': ['sha256:' + ('f' * 64 if wrong_diff else hashlib.sha256(layer_bytes).hexdigest())]}}, subject.CONFIG)
        manifest_layer = copy.deepcopy(layer)
        if wrong_size:
            manifest_layer['size'] += 1
        manifest = blob({'schemaVersion': 2, 'mediaType': subject.MANIFEST, 'config': config, 'layers': [manifest_layer]}, subject.MANIFEST)
        manifest['platform'] = {'architecture': 'amd64', 'os': 'linux'}
        index = blob({'schemaVersion': 2, 'mediaType': subject.INDEX, 'manifests': [manifest]}, subject.INDEX)
        if missing:
            del blobs['blobs/sha256/' + layer['digest'][7:]]
        if extra:
            blob(b'not referenced', subject.STATEMENT)
        blobs['index.json'] = encoded({'schemaVersion': 2, 'mediaType': subject.INDEX, 'manifests': [index]})
        blobs['oci-layout'] = encoded({'imageLayoutVersion': '1.0.0'})
        blobs['manifest.json'] = encoded([{'Config': 'blobs/sha256/' + config['digest'][7:], 'Layers': [] if docker_mismatch else ['blobs/sha256/' + layer['digest'][7:]]}])
        return blobs, index['digest']

    def run_archive(self, blobs, image, *, duplicate=False, special=None, wrong_outer=False, limit=None):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'image.tar'
            with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as tar:
                for name, data in blobs.items():
                    m = tarfile.TarInfo(name); m.size = len(data)
                    tar.addfile(m, io.BytesIO(data))
                if duplicate:
                    name, data = next(iter(blobs.items()))
                    m = tarfile.TarInfo(name); m.size = len(data)
                    tar.addfile(m, io.BytesIO(data))
                if special:
                    tar.addfile(special)
            data = archive.read_bytes()
            options = dict(expected_sha256='a' * 64 if wrong_outer else hashlib.sha256(data).hexdigest(),
                           expected_bytes=len(data), expected_image_id=image)
            if limit is not None:
                with patch.object(subject, 'MAX_EXPANDED_LAYER', limit):
                    return subject.verify(archive, **options)
            return subject.verify(archive, **options)

    def test_valid_archive_chain_and_scope(self):
        result = self.run_archive(*self.fixture())
        self.assertTrue(result['references_complete'])
        self.assertTrue(result['layer_diff_ids_verified'])
        self.assertEqual(result['layers'][0]['expanded_bytes'], 1024)
        for key in ('filesystem_union_verified', 'attestation_claims_verified', 'clean_daemon_replay_verified', 'runtime_qualified', 'redistribution_cleared'):
            self.assertIs(result[key], False)

    def test_outer_identity_checked_before_tar(self):
        with patch.object(subject.tarfile, 'open', side_effect=AssertionError('tar must not open')):
            with self.assertRaisesRegex(ValueError, 'archive identity'):
                self.run_archive_bytes_wrong_hash()

    def run_archive_bytes_wrong_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad'; path.write_bytes(b'not a tar')
            subject.verify(path, expected_sha256='a' * 64, expected_bytes=9, expected_image_id='sha256:' + 'b' * 64)

    def test_layer_descriptor_config_and_docker_tamper(self):
        for option in ('wrong_diff', 'missing', 'wrong_platform', 'wrong_size', 'docker_mismatch', 'extra'):
            with self.subTest(option=option), self.assertRaises(ValueError):
                self.run_archive(*self.fixture(**{option: True}))

    def test_blob_content_tamper(self):
        blobs, image = self.fixture()
        name = next(iter(blobs))
        blobs[name] = b'changed'
        with self.assertRaisesRegex(ValueError, 'blob identity'):
            self.run_archive(blobs, image)

    def test_duplicate_unsafe_and_link_members(self):
        with self.assertRaisesRegex(ValueError, 'duplicate archive'):
            self.run_archive(*self.fixture(), duplicate=True)
        for name, kind in (('../outside', tarfile.REGTYPE), ('link', tarfile.SYMTYPE), ('pax', tarfile.XHDTYPE)):
            m = tarfile.TarInfo(name); m.type = kind; m.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.run_archive(*self.fixture(), special=m)

    def test_decompression_is_bounded(self):
        with self.assertRaisesRegex(ValueError, 'stream size limit'):
            self.run_archive(*self.fixture(), limit=100)

    def test_duplicate_json_key(self):
        blobs, image = self.fixture()
        blobs['oci-layout'] = b'{"imageLayoutVersion":"1.0.0","imageLayoutVersion":"1.0.0"}'
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            self.run_archive(blobs, image)

    def test_wrong_expected_index(self):
        blobs, image = self.fixture()
        with self.assertRaisesRegex(ValueError, 'root image identity'):
            self.run_archive(blobs, 'sha256:' + '0' * 64)


if __name__ == '__main__':
    unittest.main()
