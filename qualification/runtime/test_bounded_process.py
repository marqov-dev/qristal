import sys
import unittest
from bounded_process import capture, ProcessError


class ProcessTests(unittest.TestCase):
    def test_capture(self):
        code,out,err=capture([sys.executable,'-c',"import sys; print('ok'); print('err',file=sys.stderr)"])
        self.assertEqual((code,out,err),(0,b'ok\n',b'err\n'))

    def test_output_overflow(self):
        for fd,limits in [(1,dict(stdout_limit=16)),(2,dict(stderr_limit=16))]:
            with self.subTest(fd=fd),self.assertRaisesRegex(ProcessError,'process_output_limit'):
                capture([sys.executable,'-c',f'import os; os.write({fd},b"x"*100000)'],**limits)

    def test_deadline_and_closed_pipes(self):
        for source in ['import time; time.sleep(30)',
                       'import os,time; os.close(1); os.close(2); time.sleep(30)',
                       'import os,time; pid=os.fork(); time.sleep(30) if pid==0 else None']:
            with self.subTest(source=source),self.assertRaisesRegex(ProcessError,'process_timeout'):
                capture([sys.executable,'-c',source],timeout=.3)

    def test_signal_exit(self):
        code,out,err=capture([sys.executable,'-c','import os,signal; os.kill(os.getpid(),signal.SIGKILL)'])
        self.assertEqual((code,out,err),(-9,b'',b''))

if __name__=='__main__':unittest.main()
