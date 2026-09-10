import json
from pathlib import Path
import shutil
import tempfile
import unittest
from check_evidence import check

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence/2026-09-11-microvm'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'passed'
        shutil.copytree(EVIDENCE / 'passed', self.root)

    def change_report(self, change):
        path = self.root / 'report.json'
        report = json.loads(path.read_text())
        change(report)
        path.write_text(json.dumps(report))

    def test_retained_success(self):
        self.assertTrue(check(self.root)['passed'])

    def test_retained_bootstrap_failure(self):
        with self.assertRaises(ValueError):
            check(EVIDENCE / 'first-attempt')

    def test_unobserved_stop(self):
        self.change_report(lambda r: r['runs'][0].update(stop_observed=False))
        with self.assertRaises(ValueError):
            check(self.root)

    def test_reused_generation(self):
        self.change_report(lambda r: r['runs'][1].update(guest_generation=r['runs'][0]['guest_generation']))
        with self.assertRaises(ValueError):
            check(self.root)

    def test_wrong_counts_even_with_matching_length(self):
        report = json.loads((self.root / 'report.json').read_text())
        row = report['runs'][2]
        path = self.root / (row['guest_id'] + '.console')
        path.write_bytes(path.read_bytes().replace(b'"10": 17', b'"01": 17'))
        with self.assertRaises(ValueError):
            check(self.root)

    def test_duplicate_result_marker(self):
        report = json.loads((self.root / 'report.json').read_text())
        row = report['runs'][0]
        path = self.root / (row['guest_id'] + '.console')
        data = path.read_bytes() + b'QB_RESULT={}\n'
        path.write_bytes(data)
        self.change_report(lambda r: r['runs'][0].update(console_bytes=len(data)))
        with self.assertRaises(ValueError):
            check(self.root)

    def test_missing_case(self):
        self.change_report(lambda r: r['runs'].pop())
        with self.assertRaises(ValueError):
            check(self.root)

    def test_path_escape(self):
        self.change_report(lambda r: r['runs'][0].update(guest_id='../outside'))
        with self.assertRaises(ValueError):
            check(self.root)

    def test_oversized_console(self):
        report = json.loads((self.root / 'report.json').read_text())
        row = report['runs'][0]
        (self.root / (row['guest_id'] + '.console')).write_bytes(b'x' * 140000)
        with self.assertRaises(ValueError):
            check(self.root)


if __name__ == '__main__':
    unittest.main()
