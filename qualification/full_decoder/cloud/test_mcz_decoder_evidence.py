import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_mcz_decoder import analyze
from patch_mcz import replace

ROOT=Path(__file__).resolve().parents[2]/'evidence/2026-09-12-mcz-decoder'

class DecoderDerivativeEvidence(unittest.TestCase):
    def test_backend_progress_is_not_caller_completion(self):
        summary=analyze(ROOT)
        self.assertEqual(summary['observed_mcz_completions'],2)
        self.assertEqual(summary['observed_backend_completions'],1)
        self.assertEqual(summary['last_checkpoint']['stage'],'backend_execute_begin')
        self.assertEqual(summary['tiny_error'],'ProcessError:process_timeout')
        self.assertFalse(summary['caller_contract_completed'])
        self.assertFalse(summary['full_decoder_qualified'])
        self.assertTrue(summary['cleanup_verified'])

    def test_header_must_be_the_qualified_version(self):
        with self.assertRaisesRegex(ValueError,'unqualified_mcz_header'):replace(b'anything',b'changed header')

    def test_changed_patch_report_cannot_override_console(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'evidence';shutil.copytree(ROOT,root)
            path=root/'result.json';report=json.loads(path.read_text())
            report['mcz_probe_identity']['patch_sha256']='0'*64;path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)

    def test_failed_transfer_cleanup_remains_unqualified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'evidence';shutil.copytree(ROOT,root)
            path=root/'transfer.json';record=json.loads(path.read_text())
            record['transfer_cleanup_verified']=False;path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)

if __name__=='__main__':unittest.main()
