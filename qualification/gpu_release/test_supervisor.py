import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from observer import AwsFailure, Journal
from supervisor import Client, CloudError, Supervisor, validate_plan

PLAN = {
    "account": "123456789012", "region": "us-east-1",
    "run": "qb-proof-" + "a" * 32,
    "image": "ami-" + "1" * 17, "subnet": "subnet-" + "2" * 17,
    "group": "sg-" + "3" * 17, "vpc": "vpc-" + "4" * 17,
    "instance_type": "g5.xlarge", "root_gib": 200,
}
INSTANCE = "i-" + "5" * 17
VOLUME = "vol-" + "6" * 17
EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-published"


class Clock:
    def __init__(self):
        self.now = 1000

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Cloud:
    def __init__(self):
        self.instance = None
        self.group_exists = True
        self.requests = []
        self.created = 0
        self.lose_launch = False
        self.fail_delete = False
        self.empty_describe = False
        self.no_volumes = False
        self.token = PLAN["run"]
        self.account = PLAN["account"]

    def __call__(self, operation, params, timeout):
        self.requests.append((operation, copy.deepcopy(params)))
        if operation == "get-caller-identity":
            return {"Account": self.account}
        if operation == "describe-security-groups":
            return {"SecurityGroups": [{
                "GroupId": PLAN["group"], "VpcId": PLAN["vpc"], "IpPermissions": [],
                "Tags": [{"Key": "QBProofRun", "Value": self.token}],
            }] if self.group_exists else []}
        if operation == "run-instances":
            if self.instance is None:
                self.created += 1
                self.instance = {
                    "InstanceId": INSTANCE, "ClientToken": PLAN["run"],
                    "SubnetId": PLAN["subnet"], "State": {"Name": "running"},
                    "BlockDeviceMappings": [] if self.no_volumes else [
                        {"Ebs": {"VolumeId": VOLUME}}],
                }
            if self.lose_launch:
                self.lose_launch = False
                raise CloudError("timeout", True)
            return {"Instances": [copy.deepcopy(self.instance)]}
        if operation == "describe-instances":
            return {"Reservations": [{"Instances": [copy.deepcopy(self.instance)]}]
                    if self.instance and not self.empty_describe else []}
        if operation == "get-console-output":
            return {"InstanceId": INSTANCE,
                    "Output": (EVIDENCE / "console-observed.txt").read_text()}
        if operation == "terminate-instances":
            self.instance["State"]["Name"] = "terminated"
            return {"TerminatingInstances": [{"InstanceId": INSTANCE}]}
        if operation == "describe-volumes":
            return {"Volumes": []}
        if operation == "delete-security-group":
            if self.fail_delete:
                raise CloudError("AccessDenied")
            self.group_exists = False
            return {}
        raise AssertionError(operation)


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "run"
        self.clock, self.cloud = Clock(), Cloud()
        Supervisor.initialize(self.root, PLAN, b"fixture", now=self.clock(),
                              seconds=60, cleanup_seconds=60)
        self.supervisor = self.resume()

    def resume(self):
        return Supervisor(self.root, self.cloud, wall=self.clock,
                          clock=self.clock, sleep=self.clock.sleep)

    def test_cli_request_is_private_and_removed(self):
        paths = []
        def run(command, **kwargs):
            path = Path(command[-1].removeprefix("file://"))
            paths.append(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"UserData": "private-canary"})
            self.assertNotIn("private-canary", " ".join(command))
            from types import SimpleNamespace
            return SimpleNamespace(returncode=0, stdout='{"ok":true}')
        with patch("supervisor.subprocess.run", side_effect=run):
            self.assertEqual(Client("us-east-1")("run-instances",
                             {"UserData": "private-canary"}, 2), {"ok": True})
        self.assertFalse(paths[0].exists())

    def test_lost_launch_response_reuses_identical_request(self):
        self.cloud.lose_launch = True
        self.supervisor.launch(b"fixture")
        requests = [params for op, params in self.cloud.requests if op == "run-instances"]
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0], requests[1])
        self.assertEqual(self.cloud.created, 1)
        self.assertEqual(Journal(self.root / "resources.json").data["volumes"], [VOLUME])
        self.assertNotIn("UserData", (self.root / "supervisor.json").read_text())

    def test_restart_recovers_result_and_exact_cleanup(self):
        self.supervisor.launch(b"fixture")
        self.clock.sleep(10)
        resumed = self.resume()
        self.assertTrue(resumed.observe(once=True))
        resumed.cleanup()
        proof = json.loads((self.root / "cleanup.json").read_text())
        self.assertEqual(proof["volume_ids"], [VOLUME])
        self.assertTrue(proof["instance_termination_observed"])
        self.assertTrue(proof["group_absent"])
        self.assertEqual(self.cloud.created, 1)
        self.assertTrue(Journal(self.root / "resources.json").data["cleanup_verified"])

    def test_restart_does_not_extend_deadline_or_launch(self):
        self.clock.sleep(61)
        with self.assertRaises(TimeoutError):
            self.resume().launch(b"fixture")
        self.assertEqual(self.cloud.created, 0)

    def test_expired_cleanup_budget_does_not_reset(self):
        self.supervisor.launch(b"fixture")
        self.clock.sleep(121)
        with self.assertRaises(TimeoutError):
            self.resume().cleanup()
        self.assertFalse((self.root / "cleanup.json").exists())

    def test_cleanup_resumes_after_group_delete_failure(self):
        self.supervisor.launch(b"fixture")
        self.cloud.fail_delete = True
        with self.assertRaises(AwsFailure):
            self.supervisor.cleanup()
        self.assertFalse((self.root / "cleanup.json").exists())
        self.assertFalse(Journal(self.root / "resources.json").data["cleanup_verified"])
        self.cloud.fail_delete = False
        self.resume().cleanup()
        self.assertTrue((self.root / "cleanup.json").exists())

    def test_missing_volume_ids_cannot_produce_cleanup_proof(self):
        self.cloud.no_volumes = True
        self.supervisor.launch(b"fixture")
        with self.assertRaisesRegex(RuntimeError, "volume_identity_unresolved"):
            self.supervisor.cleanup()
        self.assertFalse((self.root / "cleanup.json").exists())
        self.assertTrue(self.cloud.group_exists)

    def test_empty_eventual_lookup_does_not_mean_terminated(self):
        self.supervisor.launch(b"fixture")
        self.cloud.empty_describe = True
        with self.assertRaises(TimeoutError):
            self.supervisor.cleanup()
        self.assertFalse((self.root / "cleanup.json").exists())
        self.assertTrue(any(op == "terminate-instances" for op, _ in self.cloud.requests))

    def test_ambiguous_launch_absence_is_not_cleanup_proof(self):
        self.supervisor.state["launch_attempted"] = True
        self.supervisor.save()
        with self.assertRaisesRegex(RuntimeError, "launch_identity_unresolved"):
            self.supervisor.cleanup()
        self.assertFalse((self.root / "cleanup.json").exists())

    def test_changed_bootstrap_and_wrong_account_cannot_launch(self):
        with self.assertRaisesRegex(ValueError, "userdata_changed"):
            self.supervisor.launch(b"other")
        self.cloud.account = "999999999999"
        with self.assertRaisesRegex(ValueError, "account_mismatch"):
            self.supervisor.launch(b"fixture")
        self.assertEqual(self.cloud.created, 0)

    def test_group_ownership_required_for_launch_and_delete(self):
        self.cloud.token = "another-run"
        with self.assertRaisesRegex(ValueError, "group_ownership"):
            self.supervisor.launch(b"fixture")
        with self.assertRaisesRegex(ValueError, "group_ownership"):
            self.supervisor.cleanup()
        self.assertTrue(self.cloud.group_exists)

    def test_terminated_instance_may_omit_previously_bound_subnet(self):
        self.supervisor.launch(b"fixture")
        self.cloud.instance["State"]["Name"] = "terminated"
        del self.cloud.instance["SubnetId"]
        self.resume().cleanup()
        self.assertTrue((self.root / "cleanup.json").exists())

    def test_unbound_terminated_instance_cannot_omit_subnet(self):
        with self.assertRaisesRegex(ValueError, "instance_ownership"):
            self.supervisor.bind_instance({
                "InstanceId": INSTANCE, "ClientToken": PLAN["run"],
                "State": {"Name": "terminated"},
            })

    def test_bound_shutting_down_may_omit_subnet_but_not_change_token(self):
        self.supervisor.launch(b"fixture")
        retiring = copy.deepcopy(self.cloud.instance)
        retiring['State']['Name'] = 'shutting-down'
        del retiring['SubnetId']
        self.supervisor.bind_instance(retiring)
        retiring['ClientToken'] = 'different-token'
        with self.assertRaisesRegex(ValueError, 'instance_ownership'):
            self.supervisor.bind_instance(retiring)

    def test_running_or_unbound_shutting_down_cannot_omit_subnet(self):
        item = {'InstanceId': INSTANCE, 'ClientToken': PLAN['run'],
                'State': {'Name': 'shutting-down'}}
        with self.assertRaisesRegex(ValueError, 'instance_ownership'):
            self.supervisor.bind_instance(item)
        self.supervisor.launch(b'fixture')
        item['State']['Name'] = 'running'
        with self.assertRaisesRegex(ValueError, 'instance_ownership'):
            self.supervisor.bind_instance(item)

    def test_clock_regression_rejected_on_restart(self):
        self.clock.sleep(-1)
        with self.assertRaisesRegex(ValueError, "clock_moved_backwards"):
            self.resume()

    def test_repeated_run_does_not_create_second_instance(self):
        self.supervisor.launch(b"fixture")
        self.resume().launch(b"fixture")
        self.assertEqual(self.cloud.created, 1)
        self.assertEqual(sum(op == "run-instances" for op, _ in self.cloud.requests), 1)


if __name__ == "__main__":
    unittest.main()


class CpuPlanTests(unittest.TestCase):
    def test_bounded_cpu_type(self):
        validate_plan(dict(PLAN, instance_type="m7i.large", root_gib=20))
        with self.assertRaises(ValueError):
            validate_plan(dict(PLAN, instance_type="m7i.48xlarge", root_gib=20))
