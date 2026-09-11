"""Offline corruption/rebinding tests for the retained native observations."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from check_readout_evidence import DEFAULT, verify
from qualify_readout_image import sha


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / 'evidence'
        shutil.copytree(DEFAULT, self.directory)
        self.addCleanup(self.temp.cleanup)

    def change_report(self, mutate):
        path = self.directory / 'demo.stdout'
        report = json.loads(path.read_bytes())
        mutate(report)
        path.write_text(json.dumps(report))
        manifest_path = self.directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['files']['demo.stdout'] = sha(path.read_bytes())
        manifest_path.write_text(json.dumps(manifest))

    def test_retained_evidence_without_execution(self):
        with patch('subprocess.Popen', side_effect=AssertionError('execution forbidden')):
            self.assertEqual(verify(self.directory)['analytic_fixtures'], 11)

    def test_byte_corruption(self):
        with (self.directory / 'demo.stdout').open('ab') as stream:
            stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'evidence_changed'):
            verify(self.directory)

    def test_incomplete_run(self):
        (self.directory / 'manifest.json').unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.directory)

    def test_rehashed_wrong_statistics(self):
        self.change_report(lambda r: r['fixtures'][-1].update(counts={'00': 16384}))
        with self.assertRaisesRegex(ValueError, 'probability_mismatch'):
            verify(self.directory)

    def test_rehashed_changed_noise(self):
        self.change_report(lambda r: r['fixtures'][0]['options']['readout'].update(p10=.5))
        with self.assertRaisesRegex(ValueError, 'fixture_binding_changed'):
            verify(self.directory)

    def test_rehashed_relaxed_tolerance(self):
        self.change_report(lambda r: r.update(absolute_tolerance=1))
        with self.assertRaisesRegex(ValueError, 'statistical_policy_changed'):
            verify(self.directory)

    def test_rehashed_duplicate_fixture(self):
        self.change_report(lambda r: r['fixtures'].__setitem__(0, r['fixtures'][1]))
        with self.assertRaisesRegex(ValueError, 'fixture_matrix_changed'):
            verify(self.directory)

    def test_rehashed_changed_canonical_hash(self):
        self.change_report(lambda r: r['fixtures'][0].update(canonical_sha256='a'*64))
        with self.assertRaisesRegex(ValueError, 'fixture_binding_changed'):
            verify(self.directory)


if __name__ == '__main__':
    unittest.main()
