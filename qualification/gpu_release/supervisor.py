"""Operator-owned single-instance experiment supervisor; no hosted authority."""
import argparse
import base64
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from observer import AwsFailure, Journal, atomic_json, capture_console, retry_read


class CloudError(AwsFailure):
    def __init__(self, code, retryable=False):
        super().__init__(retryable)
        self.code = code


class Client:
    """Finite API surface; response bodies and stderr are never logged."""
    OPERATIONS = {
        "get-caller-identity", "run-instances", "describe-instances",
        "get-console-output", "terminate-instances", "describe-volumes",
        "describe-security-groups", "delete-security-group",
    }

    def __init__(self, region):
        self.region = region

    def __call__(self, operation, params, timeout):
        if operation not in self.OPERATIONS:
            raise ValueError("operation_not_allowed")
        service = "sts" if operation == "get-caller-identity" else "ec2"
        try:
            # The AWS CLI does not reliably consume /dev/stdin on all hosts.
            # A private temporary request avoids both that dependency and
            # credential-bearing bootstrap material in process arguments.
            with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as request:
                json.dump(params, request)
                request.flush()
                result = subprocess.run(
                    ["aws", service, operation, "--region", self.region, "--output", "json",
                     "--cli-input-json", "file://" + request.name],
                    capture_output=True, text=True, timeout=timeout,
                    env=dict(os.environ, AWS_RETRY_MODE="standard", AWS_MAX_ATTEMPTS="3",
                             AWS_PAGER=""),
                )
        except subprocess.TimeoutExpired:
            raise CloudError("timeout", True) from None
        if result.returncode:
            match = re.search(r"An error occurred \(([A-Za-z0-9.]+)\)", result.stderr)
            code = match.group(1) if match else "transport_error"
            transient = code in {
                "RequestLimitExceeded", "Throttling", "ServiceUnavailable",
                "InternalError", "DependencyViolation",
            } or any(message in result.stderr for message in (
                "Could not connect to the endpoint URL", "Connection was closed",
                "Read timeout", "Connect timeout",
            ))
            raise CloudError(code, transient)
        return json.loads(result.stdout)


def validate_plan(plan):
    required = {"account", "region", "run", "image", "subnet", "group", "vpc",
                "instance_type", "root_gib"}
    if set(plan) != required:
        raise ValueError("plan_fields")
    for key, pattern in {
        "account": r"\d{12}", "region": r"[a-z]{2}-[a-z]+-\d",
        "run": r"qb-proof-[a-f0-9]{32}", "image": r"ami-[a-f0-9]{17}",
        "subnet": r"subnet-[a-f0-9]{17}", "group": r"sg-[a-f0-9]{17}",
        "vpc": r"vpc-[a-f0-9]{17}",
    }.items():
        if not isinstance(plan[key], str) or not re.fullmatch(pattern, plan[key]):
            raise ValueError("plan_" + key)
    if plan["instance_type"] not in {"g5.xlarge", "t3.micro"}:
        raise ValueError("instance_type")
    if type(plan["root_gib"]) is not int or not 20 <= plan["root_gib"] <= 200:
        raise ValueError("root_gib")


class Supervisor:
    def __init__(self, directory, cloud, *, wall=time.time, clock=time.monotonic,
                 sleep=time.sleep):
        self.root = Path(directory)
        self.cloud, self.wall, self.clock, self.sleep = cloud, wall, clock, sleep
        self.path = self.root / "supervisor.json"
        self.state = json.loads(self.path.read_text())
        validate_plan(self.state["plan"])
        self.journal = Journal(self.root / "resources.json")
        now = wall()
        if not math.isfinite(now) or now < self.state["last_seen"]:
            raise ValueError("clock_moved_backwards")
        # Both absolute and in-process monotonic caps apply. Restart cannot reset.
        self.caps = {key: clock() + max(0, self.state[key] - now)
                     for key in ("observe_until", "cleanup_until")}

    @staticmethod
    def initialize(directory, plan, userdata, *, seconds=600, cleanup_seconds=300,
                   now=None):
        validate_plan(plan)
        if not 30 <= seconds <= 3600 or not 60 <= cleanup_seconds <= 900:
            raise ValueError("budget_bounds")
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=False)
        now = time.time() if now is None else now
        if not math.isfinite(now):
            raise ValueError("invalid_time")
        # No userdata or signed URL is retained, only its content identity.
        atomic_json(root / "supervisor.json", {
            "plan": plan, "userdata_sha256": hashlib.sha256(userdata).hexdigest(),
            "observe_until": now + seconds, "cleanup_until": now + seconds + cleanup_seconds,
            "last_seen": now, "launch_attempted": False, "phase": "prepared",
        })
        Journal(root / "resources.json").record(group=plan["group"])

    def save(self):
        atomic_json(self.path, self.state)

    def deadline(self, phase):
        now = self.wall()
        if now < self.state["last_seen"]:
            raise ValueError("clock_moved_backwards")
        self.state["last_seen"] = now
        self.save()
        return min(self.caps[phase], self.clock() + max(0, self.state[phase] - now))

    def call(self, operation, params, phase):
        end = self.deadline(phase)
        return retry_read(lambda timeout: self.cloud(operation, params, timeout), end,
                          clock=self.clock, sleep=self.sleep)

    def pause(self, phase, seconds=5):
        remaining = self.deadline(phase) - self.clock()
        if remaining <= 0:
            raise TimeoutError("supervisor_deadline")
        self.sleep(min(seconds, remaining))

    def identity(self, phase):
        account = self.call("get-caller-identity", {}, phase)["Account"]
        if account != self.state["plan"]["account"]:
            raise ValueError("account_mismatch")

    def group(self, phase):
        plan = self.state["plan"]
        groups = self.call("describe-security-groups", {
            "Filters": [{"Name": "group-id", "Values": [plan["group"]]}],
        }, phase)["SecurityGroups"]
        if not groups:
            return False
        if len(groups) != 1:
            raise ValueError("group_count")
        group = groups[0]
        tags = {tag["Key"]: tag["Value"] for tag in group.get("Tags", [])}
        if (group["GroupId"] != plan["group"] or group["VpcId"] != plan["vpc"]
                or tags.get("QBProofRun") != plan["run"]):
            raise ValueError("group_ownership")
        if group.get("IpPermissions"):
            raise ValueError("inbound_rules_not_allowed")
        return True

    def bind_instance(self, item):
        plan = self.state["plan"]
        known_terminal = (
            item.get("InstanceId") == self.journal.data["instance"]
            and item.get("State", {}).get("Name") == "terminated"
        )
        subnet_matches = item.get("SubnetId") == plan["subnet"]
        # EC2 removes placement fields after termination. This exception is
        # limited to an ID previously bound with full ownership metadata.
        subnet_retired = known_terminal and item.get("SubnetId") is None
        if item.get("ClientToken") != plan["run"] or not (subnet_matches or subnet_retired):
            raise ValueError("instance_ownership")
        self.journal.instance_response(item)
        self.state["last_instance_state"] = item["State"]["Name"]
        self.save()

    def discover(self, phase):
        plan = self.state["plan"]
        params = {"Filters": [{"Name": "client-token", "Values": [plan["run"]]}]}
        response = self.call("describe-instances", params, phase)
        items = [item for reservation in response["Reservations"]
                 for item in reservation["Instances"]]
        if len(items) > 1:
            raise ValueError("multiple_instances")
        if items:
            self.bind_instance(items[0])
            return items[0]
        return None

    def launch(self, userdata):
        plan = self.state["plan"]
        self.identity("observe_until")
        if hashlib.sha256(userdata).hexdigest() != self.state["userdata_sha256"]:
            raise ValueError("userdata_changed")
        if not self.group("observe_until"):
            raise ValueError("group_missing")
        if self.journal.data["instance"]:
            return
        # Replay always uses the same region, subnet, token and request bytes.
        self.state.update(launch_attempted=True, phase="launching")
        self.save()
        response = self.call("run-instances", {
            "ImageId": plan["image"], "InstanceType": plan["instance_type"],
            "MinCount": 1, "MaxCount": 1, "ClientToken": plan["run"],
            "NetworkInterfaces": [{"DeviceIndex": 0, "SubnetId": plan["subnet"],
                                   "Groups": [plan["group"]], "AssociatePublicIpAddress": True,
                                   "DeleteOnTermination": True}],
            "MetadataOptions": {"HttpTokens": "required", "HttpPutResponseHopLimit": 1},
            "InstanceInitiatedShutdownBehavior": "terminate",
            "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": {
                "VolumeSize": plan["root_gib"], "VolumeType": "gp3",
                "Encrypted": True, "DeleteOnTermination": True}}],
            "TagSpecifications": [{"ResourceType": kind, "Tags": [
                {"Key": "QBProofRun", "Value": plan["run"]},
                {"Key": "Name", "Value": plan["run"]},
            ]} for kind in ("instance", "volume")],
            "UserData": base64.b64encode(userdata).decode(),
        }, "observe_until")
        if len(response["Instances"]) != 1:
            raise ValueError("launch_count")
        self.bind_instance(response["Instances"][0])
        self.state["phase"] = "observing"
        self.save()

    def observe(self, *, once=False):
        self.identity("observe_until")
        while True:
            item = self.discover("observe_until")
            if item:
                output = self.call("get-console-output", {
                    "InstanceId": item["InstanceId"], "Latest": True,
                }, "observe_until")
                if output.get("InstanceId") != item["InstanceId"]:
                    raise ValueError("console_instance_mismatch")
                if capture_console(output.get("Output", ""), self.root):
                    self.state["phase"] = "result_recovered"
                    self.save()
                    return True
                if item["State"]["Name"] == "terminated":
                    raise RuntimeError("terminated_without_result")
            if once:
                return False
            self.pause("observe_until")

    def cleanup(self):
        phase = "cleanup_until"
        self.identity(phase)
        self.state["phase"] = "cleanup_pending"
        self.save()
        item = self.discover(phase)
        instance = self.journal.data["instance"]
        if self.state["launch_attempted"] and not instance:
            # An empty eventually-consistent lookup is not proof launch never ran.
            raise RuntimeError("launch_identity_unresolved")
        if instance and self.state.get("last_instance_state") != "terminated":
            self.call("terminate-instances", {"InstanceIds": [instance]}, phase)
        if instance:
            while True:
                item = self.discover(phase)
                if self.state.get("last_instance_state") == "terminated":
                    break
                self.pause(phase)
            volumes = self.journal.data["volumes"]
            if not volumes:
                raise RuntimeError("volume_identity_unresolved")
            while self.call("describe-volumes", {
                "Filters": [{"Name": "volume-id", "Values": volumes}],
            }, phase)["Volumes"]:
                self.pause(phase)
        if self.group(phase):
            try:
                self.call("delete-security-group", {
                    "GroupId": self.state["plan"]["group"],
                }, phase)
            except CloudError as error:
                if error.code != "InvalidGroup.NotFound":
                    raise
            while self.group(phase):
                self.pause(phase)
        proof = {
            "instance_id": instance, "volume_ids": self.journal.data["volumes"],
            "group_id": self.journal.data["group"],
            "instance_termination_observed": bool(instance),
            "volumes_absent": bool(instance), "group_absent": True,
            "no_launch_attempted": not self.state["launch_attempted"],
        }
        atomic_json(self.root / "cleanup.json", proof)
        self.journal.data["cleanup_verified"] = True
        atomic_json(self.journal.path, self.journal.data)
        self.state["phase"] = "cleaned"
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "run", "resume", "cleanup"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--userdata", type=Path)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--cleanup-seconds", type=int, default=300)
    parser.add_argument("--once", action="store_true",
                        help="Checkpoint one observation; intentionally leave cleanup pending.")
    args = parser.parse_args()
    if args.action == "init":
        Supervisor.initialize(args.directory, json.loads(args.plan.read_text()),
                              args.userdata.read_bytes(), seconds=args.seconds,
                              cleanup_seconds=args.cleanup_seconds)
        return
    lock = (args.directory / ".supervisor.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state = json.loads((args.directory / "supervisor.json").read_text())
    supervisor = Supervisor(args.directory, Client(state["plan"]["region"]))
    if args.action == "cleanup":
        supervisor.cleanup()
        return
    try:
        if args.action == "run":
            supervisor.launch(args.userdata.read_bytes())
        supervisor.observe(once=args.once)
    finally:
        if not args.once:
            supervisor.cleanup()


if __name__ == "__main__":
    main()
