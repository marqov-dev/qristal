"""Replay saved CPU observations; never launch or infer full-algorithm success."""
import json
from pathlib import Path
import unittest

import run  # Establish the existing bounded supervisor/console import path.
from observer import console

ROOT = Path(__file__).resolve().parents[2] / 'evidence/2026-09-12-full-decoder'


class InitialEvidence(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'cloud-initial'
        self.read = lambda name: json.loads((self.root / name).read_text())

    def test_console_checksum_recovers_exact_report(self):
        result, _, _ = console.recover('\n'.join(self.read('console-filtered.json')['records']))
        self.assertEqual(result, self.read('result.json'))
        self.assertEqual(result, self.read('recovered.json')['result'])

    def test_initialization_pass_is_distinct_from_plugin_failure(self):
        result = self.read('result.json')
        stages = {stage['name']: stage for stage in result['stages']}
        self.assertEqual(stages['input-tests']['exit_code'], 0)
        output = stages['input-tests']['stdout']
        self.assertEqual(output.count('[       OK ] FullDecoderInputValidation.'), 6)
        self.assertIn('[  PASSED  ] 6 tests.', output)
        self.assertEqual(stages['tiny-result']['exit_code'], 255)
        self.assertIn('Could not init zip archive for bundle', stages['tiny-result']['stdout'])
        self.assertNotIn('PASS: caller result contract', stages['tiny-result']['stdout'])
        self.assertEqual(result['error'], 'RuntimeError:stage_failed:tiny-result')

    def test_cleanup_recovery_retains_original_failure_and_exact_ids(self):
        initial = self.read('transfer-initial.json')
        self.assertEqual(initial['cleanup_errors'], ['vm:ValueError:instance_ownership'])
        self.assertTrue(initial['transfer_cleanup_verified'])
        cleanup, resources = self.read('cleanup.json'), self.read('resources.json')
        self.assertEqual(cleanup['instance_id'], resources['instance'])
        self.assertEqual(cleanup['volume_ids'], resources['volumes'])
        self.assertEqual(cleanup['group_id'], resources['group'])
        self.assertTrue(cleanup['instance_termination_observed'])
        self.assertTrue(cleanup['volumes_absent'])
        self.assertTrue(cleanup['group_absent'])
        self.assertLessEqual(self.read('supervisor.json')['last_seen'], self.read('supervisor.json')['cleanup_until'])
        self.assertFalse(self.read('recovery.json')['deadline_extended'])


class BundleEvidence(unittest.TestCase):
    def test_loaded_identity_and_runtime_failure_are_both_retained(self):
        root = ROOT / 'cloud-bundle'
        read = lambda name: json.loads((root / name).read_text())
        result, _, _ = console.recover('\n'.join(read('console-filtered.json')['records']))
        self.assertEqual(result, read('result.json'))
        self.assertEqual(result['loaded_core_libraries'], {
            '/work/install-xacc/plugins/libalgorithm_es.so.1.8.1': result['core_plugin_sha256']})
        stages = {stage['name']: stage for stage in result['stages']}
        self.assertEqual(stages['core-plugin-bundle']['exit_code'], 0)
        self.assertIn('[  PASSED  ] 6 tests.', stages['input-tests']['stdout'])
        self.assertEqual(stages['tiny-result']['exit_code'], 139)
        self.assertIn('Could not find iqft in Service Registry', stages['tiny-result']['stdout'])
        self.assertNotIn('PASS: caller result contract', stages['tiny-result']['stdout'])
        self.assertTrue(read('transfer.json')['vm_cleanup_verified'])
        self.assertTrue(read('transfer.json')['transfer_cleanup_verified'])
        self.assertEqual(read('transfer.json')['cleanup_errors'], [])
        self.assertTrue(read('cleanup.json')['volumes_absent'])


class QftEvidence(unittest.TestCase):
    def test_timeout_is_not_service_or_algorithm_qualification(self):
        root = ROOT / 'cloud-qft'
        read = lambda name: json.loads((root / name).read_text())
        result, _, _ = console.recover('\n'.join(read('console-filtered.json')['records']))
        self.assertEqual(result, read('result.json'))
        stages = {stage['name']: stage for stage in result['stages']}
        for name in ('qft-provider-build', 'qft-provider-bundle', 'core-plugin-build', 'input-tests'):
            self.assertEqual(stages[name]['exit_code'], 0)
        self.assertEqual(stages['tiny-result'], {'name':'tiny-result',
            'command':['/proof/out/tiny-smoke'],
            'timeout_seconds':60, 'error':'ProcessError:process_timeout'})
        self.assertEqual(result['loaded_core_libraries'], {})
        self.assertTrue(read('transfer.json')['vm_cleanup_verified'])
        self.assertTrue(read('transfer.json')['transfer_cleanup_verified'])
        self.assertEqual(read('transfer.json')['cleanup_errors'], [])


if __name__ == '__main__':
    unittest.main()
