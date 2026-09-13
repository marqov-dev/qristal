import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive
import run


class ArtifactTests(unittest.TestCase):
    def fixture(self, root):
        roots = {name: root / name for name in ('install-xacc', 'consumer', 'consumer-output', 'logs')}
        for path in roots.values():
            path.mkdir()
        (roots['install-xacc'] / 'lib.so').write_bytes(b'library')
        (roots['install-xacc'] / 'alias.so').symlink_to('lib.so')
        (roots['consumer-output'] / 'acz').write_bytes(b'consumer')
        (roots['logs'] / 'build.log').write_bytes(b'full build log')
        installed = {'lib.so': archive.digest(b'library')}
        report = {'installed_files': 1, 'installed_manifest_sha256': archive.digest(json.dumps(installed, sort_keys=True).encode()),
                  'consumer_sha256': archive.digest(b'consumer'), 'stages': {'build': {'log_sha256': archive.digest(b'full build log')}}}
        path = root / 'output.tar.gz'
        identity = archive.pack(path, report, roots)
        return path, identity, report

    def test_roundtrip_and_report_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            path, identity, report = self.fixture(Path(directory))
            self.assertTrue(archive.verify(path, identity, report)['verified'])
            with self.assertRaises(ValueError):
                archive.verify(path, identity, dict(report, extra=True))
            path.write_bytes(path.read_bytes() + b'x')
            with self.assertRaises(ValueError):
                archive.verify(path, identity, report)

    def test_path_and_link_rules(self):
        for name in ('/etc/passwd', '../out', 'a/../out', './out', 'a//b', 'a\\b'):
            with self.assertRaises(ValueError):
                archive.safe_name(name)
        for target in ('/etc/passwd', '../../escape', '..\\escape'):
            with self.assertRaises(ValueError):
                archive.safe_link('install-xacc/link', target)

    def test_tar_special_and_duplicate_members_rejected(self):
        for kind in ('hardlink', 'device', 'duplicate', 'traversal', 'setuid'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'malformed.tar.gz'
                with tarfile.open(path, 'w:gz') as stream:
                    member = tarfile.TarInfo('../escape' if kind == 'traversal' else 'entry')
                    member.mode = 0o4755 if kind == 'setuid' else 0o644
                    if kind == 'hardlink':
                        member.type, member.linkname = tarfile.LNKTYPE, 'other'
                    elif kind == 'device':
                        member.type = tarfile.CHRTYPE
                    stream.addfile(member)
                    if kind == 'duplicate':
                        stream.addfile(member)
                identity = {'bytes': path.stat().st_size, 'sha256': archive.digest(path.read_bytes())}
                with self.assertRaises(ValueError):
                    archive.verify(path, identity, {})

    def test_presign_failure_does_not_expose_error(self):
        client = Mock()
        client.generate_presigned_url.side_effect = RuntimeError('secret URL')
        with self.assertRaisesRegex(RuntimeError, '^output_presign_failed$'):
            run.sign_put(client, 'bucket', '123')

    def test_presign_scope_and_bootstrap_bound(self):
        client = Mock()
        client.generate_presigned_url.return_value = 'https://example.test/object?signature=private'
        url = run.sign_put(client, 'temporary-bucket', '123456789012')
        call = client.generate_presigned_url.call_args
        self.assertEqual(call.args, ('put_object',))
        self.assertEqual(call.kwargs['HttpMethod'], 'PUT')
        self.assertEqual(call.kwargs['Params']['Key'], 'source-output.tar.gz')
        self.assertEqual(call.kwargs['ExpiresIn'], 3900)
        original = b'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
        wrapped = run.wrap_bootstrap(original, url, '123456789012')
        self.assertLessEqual(len(wrapped), 16384)
        self.assertNotIn(url.encode(), wrapped)
        self.assertIn(b'umask 077', wrapped)

    def test_mocked_download_and_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, identity, report = self.fixture(root)
            payload = path.read_bytes()
            destination = root / 'retrieved'
            destination.mkdir()
            client = Mock()
            body = Mock()
            body.iter_chunks.return_value = [payload]
            client.get_object.return_value = {'ContentLength': len(payload), 'Body': body}
            with patch.object(run.os, 'fsync', wraps=run.os.fsync) as sync:
                result = run.download(client, {'bucket': 'b', 'account': '123'}, destination,
                                      dict(report, output_artifact=identity))
                self.assertEqual(sync.call_count, 2)
            self.assertTrue(result['verified'])
            body.close.assert_called_once()
            self.assertEqual(client.get_object.call_args.kwargs['ExpectedBucketOwner'], '123')

    def test_expired_retention_cannot_start_network(self):
        client = Mock()
        with patch.object(run.time, 'monotonic', return_value=100):
            with self.assertRaises(TimeoutError), run.retention_deadline(100.5):
                client.get_object()
        client.get_object.assert_not_called()

    def test_retention_timer_preserves_original_deadline(self):
        with patch.object(run.time, 'monotonic', return_value=100), \
             patch.object(run.signal, 'getitimer', return_value=(0, 0)), \
             patch.object(run.signal, 'getsignal', return_value=run.signal.SIG_DFL), \
             patch.object(run.signal, 'signal'), patch.object(run.signal, 'setitimer') as timer:
            with run.retention_deadline(105):
                pass
            self.assertEqual(timer.call_args_list[0].args, (run.signal.ITIMER_REAL, 5))
            self.assertEqual(timer.call_args_list[-1].args, (run.signal.ITIMER_REAL, 0))

    def test_download_size_mismatch_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            body = Mock()
            client = Mock()
            client.get_object.return_value = {'ContentLength': 9, 'Body': body}
            with self.assertRaises(ValueError):
                run.download(client, {'bucket': 'b', 'account': '123'}, Path(directory),
                             {'output_artifact': {'bytes': 8}})
            body.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
