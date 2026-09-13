import unittest
import verify


class ResultTests(unittest.TestCase):
    def test_failure_is_not_native_success(self):
        outcome=verify.verify({'kind':'qb-xacc-fresh-source-v1','error':'configure_failed','native_passed':False},b'')
        self.assertFalse(outcome['native_passed'])

    def test_conflicting_verdict_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','error':'configure_failed','native_passed':True},b'')

    def test_recovery_without_bound_stages_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','native_passed':True},b'{}')


if __name__=='__main__':unittest.main()
