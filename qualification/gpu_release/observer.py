"""Durable, bounded observation helpers for an operator-owned GPU experiment.

No launch, termination or cleanup authority. Never persist raw AWS responses.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

SPEC = importlib.util.spec_from_file_location(
    "package_console", Path(__file__).resolve().parents[1] / "gpu_package/console.py"
)
console = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(console)
ID = re.compile(r"(?:i|sg|vol)-[a-f0-9]{8,17}")
MARKER = re.compile(
    r"QB_DOWNLOAD_VERIFIED (?:candidate|supervisor)\.tar\.gz"
    r"|QB_RELEASE_IMPORT_VERIFIED sha256:[a-f0-9]{64}|QB_GPU_HOST_FINISHED"
)


def atomic_json(path, value):
    """Flush a private temporary file before replacement and directory fsync."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".observer-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            "instance": None, "group": None, "volumes": [], "cleanup_verified": False
        }

    def record(self, *, instance=None, group=None, volumes=()):
        updated = dict(self.data)
        for key, value, prefix in (("instance", instance, "i-"), ("group", group, "sg-")):
            if value is not None:
                if not ID.fullmatch(value) or not value.startswith(prefix):
                    raise ValueError("invalid_resource_id")
                if updated[key] not in (None, value):
                    raise ValueError("resource_identity_changed")
                updated[key] = value
        for volume in volumes:
            if not ID.fullmatch(volume) or not volume.startswith("vol-"):
                raise ValueError("invalid_volume_id")
        updated["volumes"] = sorted(set(updated["volumes"]) | set(volumes))
        atomic_json(self.path, updated)
        self.data = updated

    def instance_response(self, item):
        # Call immediately after run-instances or describe-instances, before
        # another AWS request. Empty later mappings must not erase known IDs.
        self.record(instance=item["InstanceId"], volumes=[
            mapping["Ebs"]["VolumeId"] for mapping in item.get("BlockDeviceMappings", [])
            if mapping.get("Ebs", {}).get("VolumeId")
        ])


class AwsFailure(RuntimeError):
    def __init__(self, retryable):
        super().__init__("aws_transient_failure" if retryable else "aws_terminal_failure")
        self.retryable = retryable


def aws_read(region, args, timeout):
    """Only observation APIs; SDK retries remain inside the subprocess timeout."""
    if tuple(args[:2]) not in {
        ("ec2", "describe-instances"), ("ec2", "get-console-output"),
        ("ec2", "describe-volumes"), ("ec2", "describe-security-groups"),
    }:
        raise ValueError("read_operation_required")
    env = dict(os.environ, AWS_RETRY_MODE="standard", AWS_MAX_ATTEMPTS="3", AWS_PAGER="")
    try:
        result = subprocess.run(
            ["aws", *args, "--region", region, "--output", "json"],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        raise AwsFailure(True) from None
    if result.returncode:
        transient = any(message in result.stderr for message in (
            "Could not connect to the endpoint URL", "Connection was closed",
            "Read timeout", "Connect timeout", "(RequestLimitExceeded)",
            "(Throttling)", "(ServiceUnavailable)", "(InternalError)",
        ))
        # Do not include stderr: it can contain URLs or credential diagnostics.
        raise AwsFailure(transient)
    return json.loads(result.stdout)


def retry_read(call, deadline, *, clock=time.monotonic, sleep=time.sleep):
    """Retry transient reads within one original monotonic deadline."""
    delay = 1
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("observer_deadline")
        try:
            return call(min(45, remaining))
        except AwsFailure as error:
            if not error.retryable:
                raise
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError("observer_deadline") from None
            sleep(min(delay, remaining))
            delay = min(delay * 2, 20)


def capture_console(output, directory):
    """Retain allowlisted tokens only; recovery still checks payload integrity."""
    directory = Path(directory)
    clean = console.native.STAMP.sub("", output)
    chunks = [match.group(0) for match in console.native.CHUNK.finditer(clean)]
    markers = MARKER.findall(clean)
    filtered = "\n".join(chunks + markers)
    # Never save an unbounded stream of records, even when no full result exists.
    if len(filtered) > 131072:
        raise ValueError("console_observation_bounds")
    atomic_json(directory / "console-filtered.json", {
        "records": chunks, "markers": markers,
    })
    try:
        result, complete, truncated = console.recover(filtered)
    except ValueError as error:
        if str(error) == "complete_copy_missing":
            return False
        raise
    atomic_json(directory / "recovered.json", {
        "result": result, "complete_records": complete.splitlines(),
        "discarded_truncated_nonfinal_fragments": truncated,
    })
    return True


def observe_once(journal, read, deadline, directory, *, clock=time.monotonic,
                 sleep=time.sleep):
    """Persist IDs before console access; result evidence is not cleanup proof."""
    instance = journal.data["instance"]
    if not instance:
        raise ValueError("instance_required")
    def request(*args):
        return retry_read(lambda timeout: read(args, timeout), deadline,
                          clock=clock, sleep=sleep)
    response = request("ec2", "describe-instances", "--instance-ids", instance)
    items = [item for reservation in response["Reservations"]
             for item in reservation["Instances"]]
    if len(items) != 1 or items[0]["InstanceId"] != instance:
        raise ValueError("instance_identity_mismatch")
    journal.instance_response(items[0])
    output = request("ec2", "get-console-output", "--instance-id", instance, "--latest")
    if output.get("InstanceId") != instance:
        raise ValueError("console_instance_mismatch")
    return capture_console(output.get("Output", ""), directory)
