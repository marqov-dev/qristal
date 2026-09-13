import hashlib
import json
from pathlib import Path
import unittest
from instrument_sparse import instrument, BEGIN, END

HERE=Path(__file__).resolve().parent
class SparseProfile(unittest.TestCase):
    def test_unknown_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'unexpected_sparse_source'):
            instrument(b'unknown')

    def test_fixture_changes_only_loaded_library_diagnostic(self):
        original=(HERE.parent/'tiny_result_smoke.cpp').read_text()
        diagnostic='      if (std::strstr(info->dlpi_name, "libsparse_simulator.so"))\n        std::cout << "LOADED_SPARSE_LIBRARY: " << info->dlpi_name << std::endl;\n'
        self.assertEqual((HERE/'tiny_profile_smoke.cpp').read_text().replace(diagnostic,''),original)


from analyze_backend_profile import parse
class ProfileValidation(unittest.TestCase):
    def test_truncation_does_not_mean_sampling_completed(self):
        output='SPARSE_PROFILE begin elapsed_us=1 phase=0 nodes=0 enabled=0 accepts=0\nSPARSE_PROFILE progress elapsed_us=12 phase=0 nodes=2 enabled=2 accepts=1\nSPARSE_COST phase=0 gate=H calls=1 accept_ns=4'
        self.assertFalse(parse(output)[0]['sampling_completed'])
        with self.assertRaisesRegex(ValueError,'cost_count_binding'):
            parse(output.replace('calls=1','calls=2'))
    def test_nonmonotonic_time_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'nonmonotonic_profile'):
            parse('SPARSE_PROFILE begin elapsed_us=10 phase=0 nodes=0 enabled=0 accepts=0\nSPARSE_PROFILE sample_begin elapsed_us=9 phase=0 nodes=0 enabled=0 accepts=0')

class InitialAttemptEvidence(unittest.TestCase):
    def test_bootstrap_failure_is_retained_with_exact_cleanup(self):
        root=HERE.parents[1]/'evidence/2026-09-12-backend-profile/attempts/initial'
        read=lambda name:json.loads((root/name).read_text())
        result=read('result.json')
        self.assertEqual(result['bootstrap_exit_code'],1)
        self.assertNotIn('stages',result)
        from observer import console
        recovered,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
        self.assertEqual(recovered,result)
        cleanup,resources,transfer=read('cleanup.json'),read('resources.json'),read('transfer.json')
        self.assertTrue(resources['cleanup_verified'])
        self.assertEqual(cleanup['instance_id'],resources['instance'])
        self.assertEqual(cleanup['volume_ids'],resources['volumes'])
        self.assertEqual(cleanup['group_id'],resources['group'])
        self.assertTrue(all(cleanup[k] for k in ('instance_termination_observed','volumes_absent','group_absent')))
        self.assertTrue(transfer['transfer_cleanup_verified'])
        self.assertEqual(transfer['cleanup_errors'],[])

class PayloadFailureEvidence(unittest.TestCase):
    def test_compact_failure_preserves_timeout_and_payload_sizes(self):
        root=HERE.parents[1]/'evidence/2026-09-12-backend-profile/attempts/bounded'
        read=lambda name:json.loads((root/name).read_text())
        from observer import console
        report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
        self.assertEqual(report,read('result.json'))
        self.assertEqual(report['error'],'evidence_payload_bounds')
        self.assertEqual(report['encoded_bytes']-128*160,348)
        self.assertEqual(report['stages'][-1]['error'],'ProcessError:process_timeout')
        self.assertTrue(read('resources.json')['cleanup_verified'])
        self.assertTrue(read('transfer.json')['transfer_cleanup_verified'])
        self.assertEqual(read('transfer.json')['cleanup_errors'],[])


class NativeProfileEvidence(unittest.TestCase):
    ROOT=HERE.parents[1]/'evidence/2026-09-12-backend-profile'
    def test_native_profile_does_not_promote_timeout(self):
        from analyze_backend_profile import analyze
        result=analyze(self.ROOT)
        self.assertFalse(result['caller_contract_completed'])
        self.assertTrue(result['cleanup_verified'])
        first,second=result['backend_calls']
        self.assertTrue(first['sampling_completed'])
        self.assertFalse(second['sampling_completed'])
        self.assertEqual(first['points'][-1]['accepts'],282207)
        self.assertEqual(first['points'][-1]['nodes'],286328)
        self.assertEqual(first['points'][-1]['elapsed_us']-first['points'][-2]['elapsed_us'],313)

    def test_changed_library_report_rejected_by_console_binding(self):
        import shutil,tempfile
        from analyze_backend_profile import analyze
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'copy';shutil.copytree(self.ROOT,root)
            p=root/'result.json';r=json.loads(p.read_text());r['sparse_plugin_sha256']='0'*64;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'console_result_binding'):analyze(root)

    def test_cleanup_failure_is_not_hidden_by_valid_timings(self):
        import shutil,tempfile
        from analyze_backend_profile import analyze
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'copy';shutil.copytree(self.ROOT,root)
            p=root/'cleanup.json';r=json.loads(p.read_text());r['volumes_absent']=False;p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'cleanup_unverified'):analyze(root)

if __name__=='__main__':unittest.main()
