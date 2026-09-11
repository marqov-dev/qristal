"""Offline evidence verification; performs no native execution or network access."""

import argparse
import hashlib
import json
from pathlib import Path

from fixtures import SHOTS, TOLERANCE, cases, check, qasm


def verify_records(records):
    expected = {case["name"]: case for case in cases()}
    seen = set()
    for record in records:
        name = record["case"]
        if name in seen or name not in expected:
            raise ValueError("case_set")
        seen.add(name)
        case = expected[name]
        check(record["counts"], case)
        if record["expected"] != case["expected"]:
            raise ValueError("expected_distribution")
        if record["program_sha256"] != hashlib.sha256(qasm(case).encode()).hexdigest():
            raise ValueError("program_binding")
    if seen != set(expected):
        raise ValueError("case_set")


def verify_gpu(report):
    if not report["owned_containers_absent"] or not report["hardware"]:
        raise ValueError("run_boundary")
    pinned = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"
    if report["image"] != pinned:
        raise ValueError("image_binding")
    seen = set()
    for result in report["results"]:
        target = result["target"]
        if target not in ("nvidia", "tensornet") or target in seen:
            raise ValueError("target_set")
        seen.add(target)
        if (
            result["gpu_count"] < 1
            or result["shots"] != SHOTS
            or result["tolerance"] != TOLERANCE
            or not result["cudaq_version"]
        ):
            raise ValueError("runtime_binding")
        required = "libcustatevec" if target == "nvidia" else "libcutensornet"
        if not any(required in lib for lib in result["libraries"]):
            raise ValueError("gpu_library_evidence")
        verify_records(result["records"])
    if seen != {"nvidia", "tensornet"}:
        raise ValueError("target_set")


def main(path):
    report = json.loads(path.read_text())
    verify_gpu(report)
    here = Path(__file__).resolve().parent
    sources = {
        name: here / name for name in ("fixtures.py", "gpu_probe.py", "run_gpu.py")
    }
    sources["bounded_process.py"] = here.parent / "runtime/bounded_process.py"
    if set(report["sources"]) != set(sources):
        raise ValueError("source_set")
    for name, source in sources.items():
        if hashlib.sha256(source.read_bytes()).hexdigest() != report["sources"][name]:
            raise ValueError("source_binding")
    cleanup = json.loads((path.parent / "cleanup.json").read_text())
    if any(
        cleanup.get(key) is not True
        for key in ("instance_terminated", "volumes_absent", "security_group_deleted")
    ):
        raise ValueError("cloud_cleanup")
    print("PASS: two GPU targets, twelve analytic cases; offline evidence only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    main(parser.parse_args().result)
