import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('core_runner',Path(__file__).with_name('run.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def test_bootstrap_scope_and_size(self):
        anchor=b'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
        result=runner.wrap(anchor,'https://example.test/object?signature=private','090208085542',12345)
        self.assertLessEqual(len(result),16384)
        self.assertIn(b'CORE_DEADLINE=12345',result)
        self.assertIn(b'umask 077',result)
        self.assertNotIn(b'https://example.test',result)
    def test_invalid_configuration_rejected(self):
        anchor=b'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
        for value in ('http://insecure','https://x\nnext','https://x"next'):
            with self.assertRaises(ValueError):runner.wrap(anchor,value,'123',100)
        with self.assertRaises(ValueError):runner.wrap(b'changed','https://x','123',100)
    def test_oversized_userdata_rejected(self):
        anchor=b'python3 /work/guest.py >/dev/console 2>/proof/guest.stderr'
        with self.assertRaises(ValueError):runner.wrap(anchor+b'x'*16384,'https://x','123',100)
