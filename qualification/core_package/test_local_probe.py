import unittest
import local_probe

class AbsenceTests(unittest.TestCase):
    def test_docker_absence_with_blank_stdout(self):
        self.assertTrue(local_probe.absence(1,b'\n',b'Error response from daemon: No such container: qpp-test','qpp-test'))

    def test_daemon_error_and_existing_container_do_not_prove_absence(self):
        self.assertFalse(local_probe.absence(1,b'',b'Cannot connect to the Docker daemon','qpp-test'))
        self.assertFalse(local_probe.absence(0,b'abc123',b'','qpp-test'))
        self.assertFalse(local_probe.absence(1,b'',b'No such container: different','qpp-test'))
