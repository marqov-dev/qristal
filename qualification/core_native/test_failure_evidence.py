"""Replay the retained native failure without running a simulator or AWS call."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/2026-09-13-core-native-configure'
spec = importlib.util.spec_from_file_location('failure_output', ROOT / 'core_output/output.py')
output = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output)


class NativeFailureEvidence(unittest.TestCase):
    def test_complete_failure_logs_and_cleanup_remain_bound(self):
        report = json.loads((EVIDENCE / 'recovered.json').read_text())['result']
        self.assertEqual(hashlib.sha256((EVIDENCE / 'protocol.json').read_bytes()).hexdigest(), report['protocol_sha256'])
        retained = output.verify(EVIDENCE / 'output.tar.gz', report['output_artifact'],
                                 {key: value for key, value in report.items() if key != 'output_artifact'})
        self.assertTrue(retained['verified'])
        self.assertFalse(retained['native_passed'])
        self.assertEqual(report['error'], 'RuntimeError:configure failed')
        self.assertEqual({name for name, stage in report['stages'].items() if stage['exit'] != 0}, {'configure'})
        self.assertNotIn('build', report['stages'])
        with tarfile.open(EVIDENCE / 'output.tar.gz', 'r:gz') as archive:
            log = archive.extractfile('logs/configure.log').read().decode()
        self.assertEqual(log.count('is_in_install_path Macro invoked with incorrect arguments'), 11)
        self.assertIn('Unknown CMake command "pybind11_add_module"', log)
        cleanup = json.loads((EVIDENCE / 'independent-cleanup.json').read_text())
        self.assertTrue(all(cleanup.values()))


class EigenFailureEvidence(unittest.TestCase):
    def test_path_fix_passed_but_nested_eigen_flow_failed(self):
        evidence = ROOT / 'evidence/2026-09-13-core-eigen-configure'
        report = json.loads((evidence / 'recovered.json').read_text())['result']
        retained = output.verify(evidence / 'output.tar.gz', report['output_artifact'],
                                 {key: value for key, value in report.items() if key != 'output_artifact'})
        self.assertTrue(retained['verified'])
        self.assertFalse(retained['native_passed'])
        self.assertEqual(report['error'], 'RuntimeError:configure failed')
        self.assertNotIn('build', report['stages'])
        with tarfile.open(evidence / 'output.tar.gz', 'r:gz') as archive:
            log = archive.extractfile('logs/configure.log').read().decode()
        self.assertNotIn('is_in_install_path Macro invoked with incorrect arguments', log)
        self.assertIn('cmake_install.cmake', log)
        self.assertIn('A REQUIRED package cannot be', log)
        self.assertIn('CMAKE_DISABLE_FIND_PACKAGE_Eigen3 is enabled', log)
        self.assertTrue(all(json.loads((evidence / 'independent-cleanup.json').read_text()).values()))


if __name__ == '__main__':
    unittest.main()
