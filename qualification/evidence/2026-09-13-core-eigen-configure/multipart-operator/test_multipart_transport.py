import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import subprocess
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('multipart', Path(__file__).with_name('multipart_transport.py'))
multipart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(multipart)


class MultipartTests(unittest.TestCase):
    def test_exact_production_identity(self):
        self.assertEqual(multipart.SHA256, '52c90c0db488806109d381410d23978e973b32446c2e080780f9aba666659650')
        self.assertEqual(multipart.BYTES, 314255620)
        self.assertEqual(multipart.WORKERS, 2)
        self.assertEqual(multipart.PART_BYTES, 8 * 1024 * 1024)

    def test_mocked_parts_persist_id_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'payload'
            payload.write_bytes(b'abcdefghijklm')
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            state_path = root / 'state.json'
            state = {'bucket': 'exact-bucket', 'key': 'cpu.tar.gz'}
            client = Mock()
            client.create_multipart_upload.return_value = {'UploadId': 'exact-id'}
            observed = {}
            lock = threading.Lock()
            def part(**kwargs):
                self.assertEqual(json.loads(state_path.read_text())['upload_id'], 'exact-id')
                self.assertEqual(kwargs['ExpectedBucketOwner'], multipart.ACCOUNT)
                data = kwargs['Body']
                self.assertEqual(kwargs['ChecksumSHA256'], base64.b64encode(hashlib.sha256(data).digest()).decode())
                with lock:
                    observed[kwargs['PartNumber']] = data
                return {'ETag': str(kwargs['PartNumber']), 'ChecksumSHA256': kwargs['ChecksumSHA256']}
            client.upload_part.side_effect = part
            client.head_object.return_value = {'ContentLength': 13, 'Metadata': {'source-sha256': digest}, 'ServerSideEncryption': 'AES256'}
            with patch.object(multipart, 'BYTES', 13), patch.object(multipart, 'SHA256', digest), patch.object(multipart, 'PART_BYTES', 5):
                multipart.upload(client, payload, state_path, state)
            self.assertEqual(b''.join(observed[n] for n in sorted(observed)), payload.read_bytes())
            self.assertEqual([p['PartNumber'] for p in client.complete_multipart_upload.call_args.kwargs['MultipartUpload']['Parts']], [1, 2, 3])
            self.assertTrue(json.loads(state_path.read_text())['verified'])

    def test_abort_exact_id_and_verify_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            multipart.save(state_path, {'bucket': 'exact', 'key': 'cpu.tar.gz', 'upload_id': 'one-id'})
            client = Mock()
            error = RuntimeError('do not expose signed request')
            error.response = {'Error': {'Code': 'NoSuchUpload'}}
            client.list_parts.side_effect = error
            multipart.abort(client, state_path)
            expected = {'Bucket': 'exact', 'Key': 'cpu.tar.gz', 'UploadId': 'one-id', 'ExpectedBucketOwner': multipart.ACCOUNT}
            client.abort_multipart_upload.assert_called_once_with(**expected)
            client.list_parts.assert_called_once_with(**expected)
            self.assertTrue(json.loads(state_path.read_text())['abort_verified'])

    def test_missing_upload_identity_never_guesses(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            multipart.save(state_path, {'bucket': 'exact', 'key': 'cpu.tar.gz', 'create_attempted': True})
            client = Mock()
            multipart.abort(client, state_path)
            client.abort_multipart_upload.assert_not_called()
            self.assertEqual(json.loads(state_path.read_text())['abort_error'], 'upload_identity_unresolved')

    def test_no_such_upload_abort_still_verifies_exact_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            multipart.save(path, {'bucket': 'exact', 'key': 'cpu.tar.gz', 'upload_id': 'one-id'})
            client = Mock()
            missing = RuntimeError('redacted')
            missing.response = {'Error': {'Code': 'NoSuchUpload'}}
            client.abort_multipart_upload.side_effect = missing
            client.list_parts.side_effect = missing
            multipart.abort(client, path)
            result = json.loads(path.read_text())
            self.assertTrue(result['abort_already_absent_response'])
            self.assertTrue(result['multipart_absence_verified'])
            self.assertNotIn('abort_error', result)
            client.list_parts.assert_called_once_with(Bucket='exact', Key='cpu.tar.gz',
                UploadId='one-id', ExpectedBucketOwner=multipart.ACCOUNT)

    def test_wrong_part_checksum_never_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'payload'
            payload.write_bytes(b'one part')
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            state_path = root / 'state.json'
            client = Mock()
            client.create_multipart_upload.return_value = {'UploadId': 'one-id'}
            client.upload_part.return_value = {'ETag': 'etag', 'ChecksumSHA256': 'incorrect'}
            with patch.object(multipart, 'BYTES', 8), patch.object(multipart, 'SHA256', digest):
                with self.assertRaisesRegex(ValueError, 'part checksum mismatch'):
                    multipart.upload(client, payload, state_path, {'bucket': 'exact', 'key': 'cpu.tar.gz'})
            client.complete_multipart_upload.assert_not_called()
            self.assertEqual(json.loads(state_path.read_text())['upload_id'], 'one-id')

    def test_lost_completion_response_preserves_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'payload'
            payload.write_bytes(b'one part')
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            state_path = root / 'state.json'
            client = Mock()
            client.create_multipart_upload.return_value = {'UploadId': 'one-id'}
            client.upload_part.side_effect = lambda **p: {'ETag': 'etag', 'ChecksumSHA256': p['ChecksumSHA256']}
            client.complete_multipart_upload.side_effect = RuntimeError('completion response lost')
            with patch.object(multipart, 'BYTES', 8), patch.object(multipart, 'SHA256', digest):
                with self.assertRaises(RuntimeError):
                    multipart.upload(client, payload, state_path, {'bucket': 'exact', 'key': 'cpu.tar.gz'})
            missing = RuntimeError('already completed')
            missing.response = {'Error': {'Code': 'NoSuchUpload'}}
            client.abort_multipart_upload.side_effect = missing
            client.list_parts.side_effect = missing
            multipart.abort(client, state_path)
            result = json.loads(state_path.read_text())
            self.assertTrue(result['object_completion_uncertain'])
            self.assertTrue(result['multipart_absence_verified'])
            self.assertFalse(result.get('verified', False))
            client.delete_object.assert_not_called()
            client.head_object.assert_not_called()

    def test_permissions_failure_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            multipart.save(state_path, {'bucket': 'exact', 'key': 'cpu.tar.gz', 'upload_id': 'one-id'})
            client = Mock()
            client.abort_multipart_upload.side_effect = RuntimeError('secret presigned URL')
            multipart.abort(client, state_path)
            self.assertNotIn('secret', state_path.read_text())
            self.assertEqual(json.loads(state_path.read_text())['abort_error'], 'RuntimeError')

    def test_wrong_payload_stops_before_create(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'wrong'
            payload.write_bytes(b'wrong')
            client = Mock()
            with self.assertRaises(ValueError):
                multipart.upload(client, payload, root / 'state.json', {'bucket': 'exact', 'key': 'cpu.tar.gz'})
            client.create_multipart_upload.assert_not_called()

    def test_timeout_uses_separate_exact_abort_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            params = {'Body': str(root / 'payload'), 'Bucket': 'exact', 'Key': 'cpu.tar.gz',
                      'ExpectedBucketOwner': multipart.ACCOUNT, 'ServerSideEncryption': 'AES256'}
            with patch.object(multipart, 'validate_payload'), patch.object(multipart.subprocess, 'run') as run:
                run.side_effect = [subprocess.TimeoutExpired('upload', 3600), subprocess.CompletedProcess('abort', 0)]
                with self.assertRaises(RuntimeError):
                    multipart.transfer(params, root)
            self.assertEqual(run.call_args_list[0].kwargs['timeout'], 3600)
            self.assertEqual(run.call_args_list[1].kwargs['timeout'], 90)
            self.assertIn('abort', run.call_args_list[1].args[0])
            self.assertTrue(json.loads((root / 'multipart-transport.json').read_text())['upload_process_timeout'])


if __name__ == '__main__':
    unittest.main()
