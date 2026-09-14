import unittest
from image_audit_guest import linkage_ok

class LinkageTests(unittest.TestCase):
    def test_missing_dependency_fails_even_with_zero_exit(self):
        self.assertFalse(linkage_ok(0,'libmissing.so => not found'))

    def test_dynamic_static_and_failed_tool(self):
        self.assertTrue(linkage_ok(0,'libc.so.6 => /lib/libc.so.6'))
        self.assertTrue(linkage_ok(1,'not a dynamic executable'))
        self.assertFalse(linkage_ok(1,'permission denied'))


class CompletionTests(unittest.TestCase):
    def test_successful_prefix_never_qualifies_an_incomplete_scan(self):
        from image_audit_guest import audit_passed
        files=[{'linkage_ok':True}];imports=[{'passed':True} for _ in range(5)]
        self.assertTrue(audit_passed(files,[],imports,True))
        for flag in (False,None,1):
            self.assertFalse(audit_passed(files,[],imports,flag))
        self.assertFalse(audit_passed(files,[],[],True))

    def test_deadline_between_directories_is_explicit_failure(self):
        import contextlib
        import io
        import json
        from unittest.mock import patch
        import image_audit_guest as audit
        output=io.StringIO()
        # Deadline expires between entering the root and its first directory.
        with patch.object(audit.time,'monotonic',side_effect=[0,0,241,241]), \
             patch.object(audit.os,'walk',return_value=iter([('/fixture',[],[])])), \
             patch.object(audit.importlib,'import_module') as imported, \
             contextlib.redirect_stdout(output):
            self.assertEqual(audit.main(),1)
        result=json.loads(output.getvalue().split(' ',1)[1])
        self.assertFalse(result['scan_complete'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['errors'][0]['error'],'AuditDeadlineExceeded')
        imported.assert_not_called()
