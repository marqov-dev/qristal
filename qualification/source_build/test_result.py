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

    def test_saved_success_and_linkage_integrity(self):
        import copy
        import gzip
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/'evidence/2026-09-13-xacc-out-of-tree'
        report=json.loads((root/'result.json').read_text())
        manifest=gzip.decompress((root/'native-input.json.gz').read_bytes())
        self.assertTrue(verify.verify(report,manifest)['native_passed'])
        self.assertEqual(verify.complete_log(report['stages']['installed-linkage']),
                         (root/'installed-linkage.txt').read_text())
        changed=copy.deepcopy(report)
        changed['stages']['installed-linkage']['head']='lost prefix'
        with self.assertRaisesRegex(ValueError,'incomplete retained log'):
            verify.verify(changed,manifest)
        changed=copy.deepcopy(report)
        changed['stages']['consumer-build']['command'][-1]='/tmp/other'
        with self.assertRaisesRegex(ValueError,'stage command'):
            verify.verify(changed,manifest)

    def test_log_recovery_rejects_gaps_and_changed_hash(self):
        import hashlib
        text='prefix-middle-suffix'
        stage={'head':text[:8], 'tail':text[-8:],
               'log_sha256':hashlib.sha256(text.encode()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'incomplete retained log'):
            verify.complete_log(stage)
        stage['head']=text[:15]
        self.assertEqual(verify.complete_log(stage),text)
        stage['log_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'incomplete retained log'):
            verify.complete_log(stage)

    def test_conflicting_verdict_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','error':'configure_failed','native_passed':True},b'')

    def test_recovery_without_bound_stages_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify({'kind':'qb-xacc-fresh-source-v1','native_passed':True},b'{}')


if __name__=='__main__':unittest.main()
