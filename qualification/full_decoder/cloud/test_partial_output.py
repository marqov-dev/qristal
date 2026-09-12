import sys
from pathlib import Path
import unittest

from capture_process import capture, ProcessError


class PartialOutput(unittest.TestCase):
    def test_timeout_retains_flushed_non_secret_checkpoint_only_when_requested(self):
        command = [sys.executable, '-c', 'import time;print("CHECKPOINT",flush=True);time.sleep(10)']
        for retain in (False, True):
            with self.subTest(retain=retain), self.assertRaises(ProcessError) as caught:
                capture(command, timeout=0.2, retain_on_error=retain)
            error = caught.exception
            self.assertEqual(str(error), 'process_timeout')
            if retain:
                self.assertEqual(error.stdout, b'CHECKPOINT\n')
                self.assertEqual(error.stderr, b'')
            else:
                self.assertFalse(hasattr(error, 'stdout'))

    def test_overflow_retains_no_more_than_declared_limit(self):
        command = [sys.executable, '-c', 'import os;os.write(1,b"x"*1000)']
        with self.assertRaises(ProcessError) as caught:
            capture(command, stdout_limit=17, stderr_limit=0, retain_on_error=True)
        self.assertEqual(str(caught.exception), 'process_output_limit')
        self.assertEqual(caught.exception.stdout, b'x' * 17)
        self.assertEqual(caught.exception.stderr, b'')
