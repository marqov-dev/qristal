import json
from pathlib import Path
import shutil
import tempfile
import unittest
from analyze_state_probe import analyze

ROOT=Path(__file__).resolve().parents[2]/'evidence/2026-09-13-sparse-state'
class StateEvidence(unittest.TestCase):
    def test_native_replay_and_limits(self):
        summary,calls=analyze(ROOT)
        self.assertEqual(summary['neutrality']['cases'],12)
        self.assertEqual(summary['neutrality']['max_complex_difference'],0)
        self.assertTrue(summary['calls'][0]['sampling_completed'])
        self.assertFalse(summary['calls'][1]['sampling_completed'])
        self.assertTrue(all(s['timed_out'] for s in summary['full_fixture'].values()))
        self.assertFalse(summary['full_decoder_qualified'])
        self.assertEqual(max(r['states'] for call in calls for r in call),24576)
    def test_o3_negative_result_is_retained(self):
        summary,calls=analyze(ROOT.with_name('2026-09-13-sparse-state-o3'))
        self.assertEqual(summary['neutrality']['cases'],12)
        self.assertEqual(summary['full_fixture']['baseline']['completed_call_ms'],[39428])
        self.assertEqual(summary['full_fixture']['observed']['completed_call_ms'],[39674])
        self.assertTrue(all(x['timed_out'] for x in summary['full_fixture'].values()))
        self.assertFalse(summary['full_decoder_qualified'])
    def test_console_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'copy';shutil.copytree(ROOT,root)
            p=root/'result.json';r=json.loads(p.read_text());r['probe_identity']['baseline_plugin']='0'*64;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)
    def test_cleanup_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'copy';shutil.copytree(ROOT,root)
            p=root/'cleanup.json';r=json.loads(p.read_text());r['volumes_absent']=False;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)
    def test_optimization_comparison_changes_only_flag(self):
        here=Path(__file__).parent
        self.assertEqual((here/'guest_state_probe.py').read_text().replace("'-O1'","'-O3'"),(here/'guest_state_probe_o3.py').read_text())

if __name__=='__main__':unittest.main()
