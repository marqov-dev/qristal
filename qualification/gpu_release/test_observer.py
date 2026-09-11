import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from observer import AwsFailure, Journal, aws_read, capture_console, observe_once, retry_read

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-published"


class Observer(unittest.TestCase):
    def test_journal_survives_restart_and_empty_mappings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.json"
            journal = Journal(path)
            journal.record(group="sg-0123456789abcdef0")
            journal.instance_response({"InstanceId": "i-0123456789abcdef0",
                                       "BlockDeviceMappings": [{"Ebs": {"VolumeId": "vol-0123456789abcdef0"}}]})
            resumed = Journal(path)
            resumed.instance_response({"InstanceId": "i-0123456789abcdef0"})
            self.assertEqual(resumed.data["volumes"], ["vol-0123456789abcdef0"])
            self.assertFalse(resumed.data["cleanup_verified"])
            with self.assertRaisesRegex(ValueError, "identity_changed"):
                resumed.record(instance="i-1123456789abcdef0")

    def test_failed_atomic_replace_preserves_old_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.json"
            journal = Journal(path)
            journal.record(group="sg-0123456789abcdef0")
            previous = path.read_bytes()
            with patch("observer.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    journal.record(instance="i-0123456789abcdef0")
            self.assertEqual(path.read_bytes(), previous)
            self.assertIsNone(journal.data["instance"])

    def test_retry_recovers_and_deadline_never_resets(self):
        now, timeouts = [0], []
        def sleep(seconds):
            now[0] += seconds
        def fail(timeout):
            timeouts.append(timeout)
            raise AwsFailure(True)
        with self.assertRaises(TimeoutError):
            retry_read(fail, 4, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(now[0], 4)
        self.assertEqual(timeouts, [4, 3, 1])
        attempts = iter([AwsFailure(True), {"ok": True}])
        def recover(timeout):
            value = next(attempts)
            if isinstance(value, Exception):
                raise value
            return value
        self.assertEqual(retry_read(recover, 8, clock=lambda: now[0], sleep=sleep), {"ok": True})

    def test_terminal_failure_is_not_retried(self):
        with self.assertRaises(AwsFailure), patch("observer.time.sleep") as sleep:
            retry_read(lambda timeout: (_ for _ in ()).throw(AwsFailure(False)), 10,
                       clock=lambda: 0, sleep=sleep)
        sleep.assert_not_called()

    def test_ids_saved_before_console_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.json"
            journal = Journal(path)
            journal.record(instance="i-0123456789abcdef0")
            def read(args, timeout):
                if args[1] == "describe-instances":
                    return {"Reservations": [{"Instances": [{
                        "InstanceId": journal.data["instance"],
                        "BlockDeviceMappings": [{"Ebs": {"VolumeId": "vol-0123456789abcdef0"}}],
                    }]}]}
                self.assertEqual(Journal(path).data["volumes"], ["vol-0123456789abcdef0"])
                raise AwsFailure(False)
            with self.assertRaises(AwsFailure):
                observe_once(journal, read, 10, directory, clock=lambda: 0)

    def test_saved_native_recovery_filters_unrelated_console(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = (EVIDENCE / "console-observed.txt").read_text()
            self.assertTrue(capture_console("PRIVATE_BOOTSTRAP_CANARY\n" + raw, directory))
            saved = json.loads((Path(directory) / "recovered.json").read_text())
            self.assertEqual(saved["result"], json.loads((EVIDENCE / "result.json").read_text()))
            for path in Path(directory).iterdir():
                self.assertNotIn("PRIVATE_BOOTSTRAP_CANARY", path.read_text())

    def test_incomplete_console_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(capture_console("unrelated log", directory))
            self.assertFalse((Path(directory) / "recovered.json").exists())

    def test_cli_rejects_mutations_and_sanitizes_errors(self):
        with self.assertRaises(ValueError):
            aws_read("us-east-1", ["ec2", "run-instances"], 1)
        with patch("observer.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "AccessDenied PRIVATE_CANARY"
            with self.assertRaises(AwsFailure) as caught:
                aws_read("us-east-1", ["ec2", "describe-instances"], 2)
            self.assertNotIn("PRIVATE_CANARY", str(caught.exception))
            self.assertFalse(caught.exception.retryable)
            self.assertEqual(run.call_args.kwargs["timeout"], 2)
            self.assertEqual(run.call_args.kwargs["env"]["AWS_MAX_ATTEMPTS"], "3")


if __name__ == "__main__":
    unittest.main()
