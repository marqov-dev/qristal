"""Offline verification of the bounded native supervisor restart evidence."""
import hashlib
import json
from pathlib import Path

from observer import console


def check(directory):
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text())
    required = {"supervisor.json", "interruption.json", "resources.json",
                "cleanup.json", "recovered.json", "verification.json"}
    if not required <= set(manifest["files"]):
        raise ValueError("manifest_missing_required")
    for name, digest in manifest["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("manifest_path")
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError("file_digest")
    state = json.loads((root / "supervisor.json").read_text())
    interruption = json.loads((root / "interruption.json").read_text())
    resources = json.loads((root / "resources.json").read_text())
    cleanup = json.loads((root / "cleanup.json").read_text())
    recovered = json.loads((root / "recovered.json").read_text())
    verification = json.loads((root / "verification.json").read_text())
    if (verification["account"] != state["plan"]["account"]
            or verification["region"] != state["plan"]["region"]
            or verification["instances_matching_original_token"] != [
                {"id": resources["instance"], "state": "terminated"}]
            or verification["exact_volume_ids"] != resources["volumes"]
            or verification["security_group_id"] != resources["group"]
            or verification["remaining_volumes"] != 0
            or verification["remaining_groups"] != 0):
        raise ValueError("independent_cleanup_verification")
    original = interruption["resources_at_interruption"]
    if interruption["exit_code"] != -9:
        raise ValueError("interruption_not_sigkill")
    if (state["observe_until"] != interruption["original_observe_until"]
            or state["cleanup_until"] != interruption["original_cleanup_until"]):
        raise ValueError("deadline_changed")
    if not interruption["observed_epoch"] < state["observe_until"] < state["cleanup_until"]:
        raise ValueError("deadline_order")
    if state["last_seen"] > state["cleanup_until"]:
        raise ValueError("cleanup_late")
    for key in ("instance", "group", "volumes"):
        if not original[key] or original[key] != resources[key]:
            raise ValueError("resource_identity")
    if (cleanup["instance_id"] != resources["instance"]
            or cleanup["group_id"] != resources["group"]
            or cleanup["volume_ids"] != resources["volumes"]):
        raise ValueError("cleanup_identity")
    if (not resources["cleanup_verified"] or state["phase"] != "cleaned"
            or not cleanup["instance_termination_observed"]
            or not cleanup["volumes_absent"] or not cleanup["group_absent"]
            or cleanup["no_launch_attempted"]):
        raise ValueError("cleanup_incomplete")
    report, _, _ = console.recover("\n".join(recovered["complete_records"]))
    if report != recovered["result"]:
        raise ValueError("result_mismatch")
    if (report["schema"] != "qb-supervisor-native-recovery-v1"
            or report["gpu_probe_returncode"] != 0 or "A10G" not in report["gpu"]
            or report["finished_epoch"] <= interruption["observed_epoch"]):
        raise ValueError("native_probe")
    return {"verified": True, "kind": "native_operator_restart_not_simulator_qualification",
            "instance": resources["instance"], "volume_ids": resources["volumes"]}


if __name__ == "__main__":
    import sys
    print(json.dumps(check(Path(sys.argv[1])), indent=2))
