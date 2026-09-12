import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_qft import analyze

EVIDENCE=Path(__file__).resolve().parents[2]/'evidence/2026-09-12-qft-states'


class NativeQftEvidence(unittest.TestCase):
    def test_native_vectors_and_decoder_timeout_remain_separate(self):
        records,summary=analyze(EVIDENCE)
        self.assertEqual(len(records),70)
        self.assertLess(summary['max_abs_error_by_mode']['qft'],1e-6)
        self.assertEqual(summary['decoder_stage']['error'],'ProcessError:process_timeout')
        output=summary['decoder_stage']['partial_stdout']
        self.assertIn('SERVICE_PRESENT: iqft',output)
        self.assertIn('Current exponential search iteration = 1',output)
        self.assertNotIn('CHECKPOINT decoder_execute_complete',output)

    def test_changed_decoded_result_does_not_match_console(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'evidence';shutil.copytree(EVIDENCE,root)
            path=root/'result.json';record=json.loads(path.read_text())
            record['loaded_qft_libraries']={};path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)

    def test_wrong_disk_or_failed_transfer_cannot_qualify(self):
        for filename,key,value in (('cleanup.json','volume_ids',['vol-wrong']),
                                   ('transfer.json','transfer_cleanup_verified',False)):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)/'evidence';shutil.copytree(EVIDENCE,root)
                path=root/filename;record=json.loads(path.read_text());record[key]=value
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)
