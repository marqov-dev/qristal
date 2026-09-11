"""Offline verification of saved qualification observations, not acceptance authority."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "accelerators"))
from adapter import IMAGE, VERSION, parse
from console import decode
from fixtures import cases, check


def verify(report):
    expected = {case["name"]: case for case in cases()}
    if (
        report["image"] != IMAGE
        or not report["owned_containers_absent"]
        or not report["gpu_processes_absent"]
    ):
        raise ValueError("run_boundary")
    observed = set()
    for record in report["records"] + [report["recovery"]]:
        candidate = record["candidate"]
        artifact = record["artifact"]
        raw = json.dumps(artifact, sort_keys=True).encode()
        parse(raw, candidate["input_sha256"])
        case = expected[record["case"]]
        if (
            artifact["gates"] != [list(g) for g in case["gates"]]
            or artifact["qubits"] != case["qubits"]
        ):
            raise ValueError("circuit_binding")
        if (
            candidate["schema"] != "qristal.cudaq-candidate/v1"
            or candidate["adapter"] != VERSION
            or candidate["runtime_image"] != IMAGE
            or candidate["target"] != artifact["target"]
            or candidate["qubits"] != artifact["qubits"]
            or candidate["shots"] != artifact["shots"]
            or candidate["shots"] != 16384
            or candidate["seed"] != artifact["seed"]
            or candidate["seed"] != 42
            or candidate["bit_order"] != "logical-qubit-zero-first"
            or candidate["gpu_count"] < 1
            or not candidate["cudaq_version"]
            or candidate["adapter_sha256"] != report["sources"]["adapter.py"]
            or record["exit_code"] != 0
            or record["stopped_observed"] is not True
        ):
            raise ValueError("candidate_binding")
        check(candidate["counts"], case)
        selected = (
            "libnvqir-cusvsim-fp64.so"
            if artifact["target"] == "nvidia"
            else "libnvqir-tensornet.so"
        )
        if not any(selected in path for path in candidate["libraries"]):
            raise ValueError("simulator_library")
    for record in report["records"]:
        key = record["candidate"]["target"], record["case"]
        if key in observed:
            raise ValueError("duplicate_case")
        observed.add(key)
    if observed != {(t, c) for t in ("nvidia", "tensornet") for c in expected}:
        raise ValueError("case_matrix")
    if (
        report["recovery"]["case"] != "x-first"
        or report["recovery"]["candidate"]["target"] != "nvidia"
    ):
        raise ValueError("recovery_case")
    modes = {}
    for fault in report["faults"]:
        if fault["mode"] in modes:
            raise ValueError("duplicate_fault")
        modes[fault["mode"]] = fault["outcome"]
        if (
            fault["owned_gpu_context_observed"] is not True
            or fault["stopped_observed"] is not True
            or fault["exit_code"] != 137
        ):
            raise ValueError("fault_boundary")
    if modes != dict(
        cancel="requested_kill",
        timeout="process_timeout",
        overflow="process_output_limit",
    ):
        raise ValueError("fault_matrix")


def main(directory):
    report = json.loads((directory / "result.json").read_text())
    verify(report)
    if decode((directory / "console-chunks.txt").read_text()) != report:
        raise ValueError("console_binding")
    paths = {
        name: HERE / name for name in ("adapter.py", "fault_workload.py", "qualify.py")
    }
    paths.update(
        {
            "fixtures.py": HERE.parent / "accelerators/fixtures.py",
            "bounded_process.py": HERE.parent / "runtime/bounded_process.py",
        }
    )
    if set(report["sources"]) != set(paths):
        raise ValueError("source_set")
    for name, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != report["sources"][name]:
            raise ValueError("source_binding")
    cleanup = json.loads((directory / "cleanup.json").read_text())
    if any(
        cleanup.get(k) is not True
        for k in ("instance_terminated", "volumes_absent", "security_group_deleted")
    ):
        raise ValueError("cloud_cleanup")
    print(
        "PASS: 12 native adapter cases, 3 GPU-context lifecycle faults, recovery and cleanup evidence"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    main(parser.parse_args().directory)
