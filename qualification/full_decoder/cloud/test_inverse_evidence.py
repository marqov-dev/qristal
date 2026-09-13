import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_inverse import analyze

ROOT=Path(__file__).resolve().parents[2]/'evidence/2026-09-13-structured-inverse'
class InverseEvidence(unittest.TestCase):
    def test_candidate_pass_and_legacy_discrepancies_remain_distinct(self):
        report,_,_=analyze(ROOT)
        self.assertEqual(report['qpp']['candidate_matrix_cases'],140)
        self.assertEqual(report['qpp']['legacy_mismatches'],4)
        self.assertEqual(report['sparse_interference']['cases'],20)
        self.assertTrue(report['cleanup_verified'])
        self.assertFalse(report['full_decoder_qualified'])
    def test_fabricated_report_cannot_override_console(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'copy';shutil.copytree(ROOT,root)
            p=root/'result.json';r=json.loads(p.read_text());r['binary_sha256']['inverse-checks']='0'*64;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)
    def test_cleanup_failure_blocks_qualification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'copy';shutil.copytree(ROOT,root)
            p=root/'cleanup.json';r=json.loads(p.read_text());r['volumes_absent']=False;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)
    def test_both_failed_attempts_are_preserved(self):
        for name in ('initial','qpp-legacy-lowering'):
            root=ROOT/'attempts'/name
            r=json.loads((root/'result.json').read_text())
            self.assertEqual(r['error'],'RuntimeError:stage_failed:inverse-qpp')
            self.assertEqual(r['stages'][-1]['exit_code'],1)
            self.assertTrue(json.loads((root/'resources.json').read_text())['cleanup_verified'])
            with self.assertRaisesRegex(ValueError,'native_failure'):analyze(root)

if __name__=='__main__':unittest.main()
