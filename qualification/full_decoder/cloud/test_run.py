import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import run


class Lifecycle(unittest.TestCase):
    def exercise(self, fail=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / 'artifact'
            artifact.mkdir()
            (artifact / 'cpu.tar.gz').write_bytes(b'public fixture')
            (artifact / 'archive.json').write_text(json.dumps({
                'sha256': hashlib.sha256(b'public fixture').hexdigest(), 'bytes': 14}))
            bucket_exists = False
            operations = []
            def api(service, operation, params):
                nonlocal bucket_exists
                operations.append(operation)
                if operation == fail:
                    raise run.ApiError(operation + ':injected')
                if operation == 'get-caller-identity':
                    return {'Account': run.ACCOUNT}
                if operation == 'create-bucket':
                    bucket_exists = True
                if operation == 'delete-bucket':
                    bucket_exists = False
                if operation == 'head-bucket' and not bucket_exists:
                    raise run.ApiError('head-bucket:404')
                if operation == 'create-security-group':
                    return {'GroupId': 'sg-' + '1' * 17}
                if operation == 'describe-security-groups':
                    return {'SecurityGroups': []}
                return {}
            supervisor = MagicMock()
            if fail in ('launch', 'observe', 'cleanup'):
                getattr(supervisor, fail).side_effect = RuntimeError('injected')
            supervisor_type = MagicMock(return_value=supervisor)
            output = io.StringIO()
            with patch.object(run, 'aws', side_effect=api), \
                 patch.object(run, 'Supervisor', supervisor_type), \
                 patch.object(run.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'https://example.test/private?signature=DO_NOT_RETAIN', '')), \
                 patch.object(run.sys, 'argv', ['run', str(artifact), str(root / 'state')]), \
                 contextlib.redirect_stdout(output):
                code = run.main()
            state = json.loads((root / 'state/transfer.json').read_text())
            self.assertNotIn('DO_NOT_RETAIN', output.getvalue())
            self.assertNotIn('DO_NOT_RETAIN', json.dumps(state))
            self.assertFalse(bucket_exists)
            self.assertTrue(state['transfer_cleanup_verified'])
            if supervisor_type.called:
                supervisor.cleanup.assert_called_once()
            return code, state, operations

    def test_success_cleans_both_resource_sets(self):
        code, state, _ = self.exercise()
        self.assertEqual(code, 0)
        self.assertTrue(state['vm_cleanup_verified'])

    def test_failed_observation_still_cleans(self):
        self.assertEqual(self.exercise('observe')[0], 1)

    def test_uncertain_launch_still_invokes_supervisor_cleanup(self):
        self.assertEqual(self.exercise('launch')[0], 1)

    def test_vm_cleanup_failure_does_not_skip_transfer_cleanup(self):
        code, state, _ = self.exercise('cleanup')
        self.assertEqual(code, 1)
        self.assertTrue(state['cleanup_errors'])

    def test_failure_before_launch_cleans_transfer(self):
        for operation in ('put-public-access-block', 'put-object', 'create-security-group'):
            with self.subTest(operation=operation):
                self.assertEqual(self.exercise(operation)[0], 1)

    def test_bootstrap_shell_syntax(self):
        result = subprocess.run(['bash', '-n'], input=run.bootstrap('https://example.test/a?b=c', 'a' * 64), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_rejects_shell_injection(self):
        for url in ("https://example.test/'bad", 'https://example.test/\nbad'):
            with self.assertRaises(ValueError):
                run.bootstrap(url, 'a' * 64)


if __name__ == '__main__':
    unittest.main()
