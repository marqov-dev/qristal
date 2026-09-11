"""Validate retained package observations against source, not hosted authority."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gpu_adapter"))
spec = importlib.util.spec_from_file_location(
    "native_checker", HERE.parent / "gpu_adapter/check_evidence.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def verify(report):
    native.verify(report)
    build = report["build"]
    image = build["image_id"]
    if not re.fullmatch("sha256:[a-f0-9]{64}", image) or build["base"] != native.IMAGE:
        raise ValueError("build_identity")
    files = {
        "adapter.py": HERE.parent / "gpu_adapter/adapter.py",
        "fault_workload.py": HERE.parent / "gpu_adapter/fault_workload.py",
        "inventory.py": HERE / "inventory.py",
    }
    expected = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in files.items()
    }
    inventory = report["inventory"]
    if (
        build["files"] != expected
        or inventory["observed_files"] != expected
        or inventory["payload"] != {"base": native.IMAGE, "files": expected}
    ):
        raise ValueError("payload_binding")
    if (
        build["dockerfile_sha256"]
        != hashlib.sha256((HERE / "Dockerfile").read_bytes()).hexdigest()
    ):
        raise ValueError("recipe_binding")
    if (
        inventory["architecture"] != "x86_64"
        or not inventory["python_packages"]
        or not inventory["dpkg"]
    ):
        raise ValueError("inventory_missing")
    observations = report["container_observations"]
    # Inventory + 12 cases + 2 negatives + 3 faults + recovery.
    if len(observations) != 19 or any(
        o != {"image": image, "mounts": [{"destination": "/inputs", "rw": False}]}
        for o in observations
    ):
        raise ValueError("container_boundary")
    negatives = report["negatives"]
    if len(negatives) != 2 or {n["mode"] for n in negatives} != {
        "invalid-input",
        "no-gpu",
    }:
        raise ValueError("negative_matrix")
    if any(
        type(n["exit_code"]) is not int
        or n["exit_code"] == 0
        or n["candidate_absent"] is not True
        or n["stopped_observed"] is not True
        for n in negatives
    ):
        raise ValueError("negative_boundary")


def main(directory):
    report = json.loads((directory / "result.json").read_text())
    verify(report)
    if native.decode((directory / "console-chunks.txt").read_text()) != report:
        raise ValueError("console_binding")
    recovery_spec = importlib.util.spec_from_file_location(
        "package_recovery", HERE / "console.py"
    )
    recovery_module = importlib.util.module_from_spec(recovery_spec)
    recovery_spec.loader.exec_module(recovery_module)
    recovered, complete, discarded = recovery_module.recover(
        (directory / "console-observed.txt").read_text()
    )
    if (
        recovered != report
        or complete != (directory / "console-chunks.txt").read_text()
    ):
        raise ValueError("recovery_binding")
    recovery_note = json.loads((directory / "console-recovery.json").read_text())
    if discarded != recovery_note["discarded_truncated_nonfinal_fragments"]:
        raise ValueError("recovery_note")
    for name, expected in json.loads(
        (directory / "source-hashes.json").read_text()
    ).items():
        if hashlib.sha256((HERE.parent / name).read_bytes()).hexdigest() != expected:
            raise ValueError("staged_source_binding")
    cleanup = json.loads((directory / "cleanup.json").read_text())
    if any(
        cleanup.get(k) is not True
        for k in ("instance_terminated", "volumes_absent", "security_group_deleted")
    ):
        raise ValueError("cleanup")
    print(
        "PASS: packaged identity, input-only mounts, 12 circuits, 2 negatives, 3 faults, recovery and cleanup"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    main(parser.parse_args().directory)
