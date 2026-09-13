import json
from pathlib import Path
import shutil
import tempfile
import unittest

from analyze_search import analyze, checkpoints
from instrument_search import instrument


class TraceBoundaries(unittest.TestCase):
    def test_changed_source_rejected_before_instrumentation(self):
        with self.assertRaisesRegex(ValueError, 'unexpected_core_source'):
            instrument(b'not the audited source')

    def test_missing_trace_is_not_a_profile(self):
        with self.assertRaisesRegex(ValueError, 'missing_trace'):
            checkpoints('Current exponential search iteration = 1')

    def test_bad_timestamps_rejected(self):
        with self.assertRaisesRegex(ValueError, 'nonmonotonic_trace'):
            checkpoints('SEARCH_TRACE inverse_expand_begin elapsed_ms=12 count=-1\n'
                        'SEARCH_TRACE inverse_expand_end elapsed_ms=11 count=4')

    def test_separate_execute_calls_reset_clock(self):
        result = checkpoints('SEARCH_TRACE backend_execute_end elapsed_ms=50 count=-1\n'
                             'SEARCH_TRACE execute_begin elapsed_ms=0 count=-1')
        self.assertEqual(len(result), 2)

    def test_malformed_trace_rejected(self):
        with self.assertRaisesRegex(ValueError, 'malformed_trace'):
            checkpoints('SEARCH_TRACE mcz_expand_begin elapsed_ms=unknown count=23')


class NativeSearchEvidence(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]/'evidence/2026-09-12-search-trace'

    def test_trace_locates_expansion_without_claiming_a_result(self):
        result = analyze(self.root)
        self.assertEqual(result['last_checkpoint']['stage'], 'mcz_expand_begin')
        self.assertEqual(result['last_checkpoint']['count'], 18)
        self.assertEqual(result['tiny_error'], 'ProcessError:process_timeout')
        self.assertFalse(result['full_decoder_qualified'])
        self.assertTrue(result['cleanup_verified'])

    def test_changed_source_report_cannot_replace_console_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'evidence'
            shutil.copytree(self.root, root)
            path = root/'result.json'
            data = json.loads(path.read_text())
            data['search_trace_identity']['source_sha256'] = '0'*64
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'console_result_binding'):
                analyze(root)

    def test_cleanup_must_bind_the_recorded_disk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'evidence'
            shutil.copytree(self.root, root)
            path = root/'cleanup.json'
            data = json.loads(path.read_text())
            data['volume_ids'] = ['vol-wrong']
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'cleanup_unverified'):
                analyze(root)


if __name__ == '__main__':
    unittest.main()
