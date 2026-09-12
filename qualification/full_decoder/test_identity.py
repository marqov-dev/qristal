import copy
from pathlib import Path
import tempfile
import unittest
import subprocess
from types import SimpleNamespace
from identity import SOURCE_FILES, TEST_NAMES, accepted, fingerprint, cleanup_owned


class NativeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        hashes = {name: 'a' * 64 for name in SOURCE_FILES}
        self.record = dict(exit_code=0, owned_container_absent=True,
                           source_before=hashes, source_after=dict(hashes))
        self.output = ('\n'.join('[       OK ] FullDecoderInputValidation.' + name + ' (1 ms)'
                                 for name in TEST_NAMES) + '\n[  PASSED  ] 6 tests.\n').encode()

    def test_accepts_complete_bound_native_test_result(self):
        self.assertTrue(accepted(self.record, self.output))

    def test_rejects_zero_tests_and_missing_required_case(self):
        self.assertFalse(accepted(self.record, b'[  PASSED  ] 0 tests.'))
        self.assertFalse(accepted(self.record, self.output.replace(TEST_NAMES[0].encode(), b'OtherCase')))

    def test_rejects_failure_timeout_or_unverified_cleanup(self):
        for update in ({'exit_code': 1}, {'harness_error': 'ProcessError:process_timeout'},
                       {'owned_container_absent': False}):
            self.assertFalse(accepted(dict(self.record, **update), self.output))

    def test_rejects_changed_or_missing_header_identity(self):
        altered = copy.deepcopy(self.record)
        altered['source_after'][SOURCE_FILES[2]] = 'b' * 64
        self.assertFalse(accepted(altered, self.output))
        altered['source_before'].pop(SOURCE_FILES[2])
        self.assertFalse(accepted(altered, self.output))

    def test_fingerprint_detects_header_edits_and_missing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in SOURCE_FILES:
                path = Path(directory) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('original')
            before = fingerprint(directory)
            (Path(directory) / SOURCE_FILES[2]).write_text('changed')
            self.assertNotEqual(before, fingerprint(directory))
            (Path(directory) / SOURCE_FILES[0]).unlink()
            with self.assertRaises(FileNotFoundError):
                fingerprint(directory)


class CleanupTests(unittest.TestCase):
    def test_exact_owned_cleanup_and_absence(self):
        commands = []
        outputs = iter(['owned-id\n', '', ''])
        def run(command, **options):
            commands.append(command)
            self.assertEqual(options['timeout'], 20)
            return SimpleNamespace(stdout=next(outputs))
        self.assertEqual(cleanup_owned('qb-full-decoder-test', run), {'owned_container_absent': True})
        self.assertEqual(commands[1], ['docker', 'rm', '-f', 'owned-id'])
        self.assertIn('label=qb.full-decoder=qb-full-decoder-test', commands[0])
        self.assertEqual(commands[0], commands[2])

    def test_failed_cleanup_stays_unverified(self):
        def run(command, **options):
            raise subprocess.TimeoutExpired(command, 20)
        result = cleanup_owned('qb-full-decoder-test', run)
        self.assertFalse(result['owned_container_absent'])
        self.assertEqual(result['cleanup_error'], 'TimeoutExpired')
