import unittest
import verify


class ResultTests(unittest.TestCase):
    def test_failure_is_not_native_success(self):
        outcome=verify.verify({'kind':'qb-xacc-fresh-source-v1','error':'configure_failed','native_passed':False},b'')
        self.assertFalse(outcome['native_passed'])

    def test_retained_native_failure_stays_failure(self):
        import json
        from pathlib import Path
        path=Path(__file__).resolve().parents[1]/'evidence/2026-09-13-xacc-source-build/result.json'
        report=json.loads(path.read_text())
        self.assertFalse(verify.verify(report,b'')['native_passed'])
        self.assertIn('/work/xacc/dist',report['stages']['build']['tail'])

    def test_conflicting_verdict_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','error':'configure_failed','native_passed':True},b'')

    def test_recovery_without_bound_stages_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','native_passed':True},b'{}')


if __name__=='__main__':unittest.main()
