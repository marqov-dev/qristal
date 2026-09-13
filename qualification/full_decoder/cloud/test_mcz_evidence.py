import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_mcz import analyze
import run
from observer import console

ROOT=Path(__file__).resolve().parents[2]/'evidence/2026-09-12-mcz-equivalence'

class NativeMCZEvidence(unittest.TestCase):
    def test_saved_native_subset(self):
        summary,states,counts=analyze(ROOT)
        self.assertEqual((len(states),len(counts)),(42,158))
        self.assertLess(summary['qpp']['maximum_complex_error'],1e-10)
        self.assertTrue(summary['cleanup_verified'])
        self.assertFalse(summary['full_decoder_qualified'])

    def test_first_failure_retained_without_later_stage_claims(self):
        root=ROOT/'attempts/initial'
        read=lambda n:json.loads((root/n).read_text())
        report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
        self.assertEqual(report,read('result.json'))
        self.assertEqual([s['name'] for s in report['stages']],['mcz-build','mcz-negative'])
        self.assertIn('clone_lost_disabled',report['stages'][-1]['stderr'])
        self.assertTrue(read('transfer.json')['vm_cleanup_verified'])
        self.assertTrue(read('transfer.json')['transfer_cleanup_verified'])
        with self.assertRaisesRegex(ValueError,'native_failure'):analyze(root)

    def test_changed_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'evidence';shutil.copytree(ROOT,root)
            path=root/'result.json';report=json.loads(path.read_text())
            report['binary_sha256']['mcz-checks']='0'*64;path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)

    def test_wrong_disk_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'evidence';shutil.copytree(ROOT,root)
            path=root/'cleanup.json';record=json.loads(path.read_text())
            record['volume_ids']=['vol-wrong'];path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)

if __name__=='__main__':unittest.main()
