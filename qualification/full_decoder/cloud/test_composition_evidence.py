import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_composition import analyze

ROOT=Path(__file__).resolve().parents[2]/'evidence/2026-09-13-phase-composition'
class EvidenceTests(unittest.TestCase):
    def test_replay_and_boundaries(self):
        report,states,counts=analyze(ROOT)
        self.assertEqual(len(states),8)
        self.assertEqual(report['inventory']['preparation']['nodes'],95425)
        self.assertEqual(report['inventory']['legacy_inverse']['eligible_control_blocks'],0)
        self.assertTrue(report['cleanup_verified'])
        self.assertFalse(report['full_decoder_qualified'])
        self.assertLess(max(x['outer_one_probability'] for x in states),1e-20)
    def test_console_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'evidence';shutil.copytree(ROOT,root)
            p=root/'result.json';r=json.loads(p.read_text());r['inventory_intentional_stop']=False;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)
    def test_cleanup_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'evidence';shutil.copytree(ROOT,root)
            p=root/'cleanup.json';r=json.loads(p.read_text());r['volumes_absent']=False;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)

if __name__=='__main__':unittest.main()
