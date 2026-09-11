"""Reuse native adapter tests with packaged code and input-only mounts."""

import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zlib

HERE = Path(__file__).resolve().parent
for path in ("gpu_adapter", "accelerators", "runtime"):
    sys.path.insert(0, str(HERE.parent / path))
spec = importlib.util.spec_from_file_location(
    "native_qualification", HERE.parent / "gpu_adapter/qualify.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
from bounded_process import capture  # noqa: E402


def command(name, identity, inputs, entry, gpu=True):
    if not re.fullmatch("sha256:[a-f0-9]{64}", identity):
        raise ValueError("immutable_image_required")
    translated = []
    for argument in entry:
        if argument.startswith("/probe/inputs/"):
            translated.append("/inputs/" + Path(argument).name)
        elif argument in ("/probe/adapter.py", "/probe/fault_workload.py"):
            translated.append("/opt/marqov-qb/" + Path(argument).name)
        else:
            translated.append(argument)
    return [
        "create",
        "--pull",
        "never",
        "--name",
        name,
        "--label",
        "qb.adapter=" + name,
        *(
            ["--gpus", "all", "--env", "NVIDIA_VISIBLE_DEVICES=all"]
            if gpu
            else ["--env", "NVIDIA_VISIBLE_DEVICES=void"]
        ),
        "--network",
        "none",
        "--cpus",
        "4",
        "--memory",
        "12g",
        "--memory-swap",
        "12g",
        "--pids-limit",
        "512",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,exec,size=512m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "65532:65532",
        "--log-opt",
        "max-size=1m",
        "--log-opt",
        "max-file=1",
        "--mount",
        f"type=bind,source={inputs},target=/inputs,readonly",
        "--entrypoint",
        "python3",
        identity,
        "-B",
        *translated,
    ]


def main(output, build):
    output.mkdir()
    inputs = output / "inputs"
    inputs.mkdir(mode=0o755)
    output.chmod(0o755)
    lock = json.loads(build.read_text())
    identity = lock["image_id"]
    inspections = []

    def create(name, entry, gpu=True):
        native.docker(*command(name, identity, inputs.resolve(), entry, gpu))
        inspected = json.loads(native.docker("inspect", name))[0]
        mounts = inspected["Mounts"]
        if (
            inspected["Image"] != identity
            or len(mounts) != 1
            or mounts[0]["Destination"] != "/inputs"
            or mounts[0]["RW"]
        ):
            raise RuntimeError("packaged_mount_or_identity")
        inspections.append(
            dict(
                image=inspected["Image"],
                mounts=[dict(destination=m["Destination"], rw=m["RW"]) for m in mounts],
            )
        )

    native.create = create
    inventory_name = "qb-adapter-" + uuid.uuid4().hex
    try:
        create(inventory_name, ["/opt/marqov-qb/inventory.py"], False)
        code, raw, error = capture(
            ["docker", "start", "-a", inventory_name],
            timeout=120,
            stdout_limit=100000,
            stderr_limit=16384,
        )
        if code:
            raise RuntimeError(
                "inventory_failure: " + error[-6000:].decode(errors="replace")
            )
        inventory = json.loads(raw)
        if (
            inventory["observed_files"] != lock["files"]
            or inventory["payload"]["base"] != lock["base"]
        ):
            raise RuntimeError("payload_binding")
    finally:
        native.remove(inventory_name)
    records = [
        native.run_case(target, case, inputs)
        for target in ("nvidia", "tensornet")
        for case in native.cases()
    ]
    negatives = []
    for mode in ("invalid-input", "no-gpu"):
        raw = (
            b"{}"
            if mode == "invalid-input"
            else json.dumps(records[0]["artifact"], sort_keys=True).encode()
        )
        file = inputs / (mode + ".json")
        file.write_bytes(raw)
        file.chmod(0o644)
        name = "qb-adapter-" + uuid.uuid4().hex
        try:
            create(
                name,
                [
                    "/probe/adapter.py",
                    "/probe/inputs/" + file.name,
                    "--sha256",
                    hashlib.sha256(raw).hexdigest(),
                ],
                mode != "no-gpu",
            )
            code, stdout, stderr = capture(
                ["docker", "start", "-a", name],
                timeout=120,
                stdout_limit=131072,
                stderr_limit=16384,
            )
            state = json.loads(native.docker("inspect", name))[0]["State"]
            if (
                code == 0
                or stdout.strip()
                or state["Running"]
                or state["ExitCode"] == 0
            ):
                raise RuntimeError("negative_candidate_or_running")
            negatives.append(
                dict(
                    mode=mode,
                    exit_code=state["ExitCode"],
                    candidate_absent=True,
                    stopped_observed=True,
                )
            )
        finally:
            native.remove(name)
    faults = [native.fault(mode) for mode in ("cancel", "timeout", "overflow")]
    recovery = native.run_case("nvidia", native.cases()[0], inputs)
    report = dict(
        scope="packaged standalone qualification; not hosted acceptance",
        image=native.IMAGE,
        build=lock,
        inventory=inventory,
        container_observations=inspections,
        records=records,
        negatives=negatives,
        faults=faults,
        recovery=recovery,
        owned_containers_absent=True,
        gpu_processes_absent=True,
        hardware=subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            timeout=15,
        )
        .decode()
        .strip(),
        sources={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (HERE.parent / "gpu_adapter").glob("*.py")
        },
    )
    raw = json.dumps(report, sort_keys=True).encode()
    (output / "result.json").write_bytes(raw)
    encoded = base64.b64encode(zlib.compress(raw)).decode()
    parts = [encoded[i : i + 160] for i in range(0, len(encoded), 160)]
    if len(parts) > 128 or len(raw) > 131072:
        raise RuntimeError("console_bounds")
    digest = hashlib.sha256(raw).hexdigest()
    for index, part in enumerate(parts):
        print(f"QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}", flush=True)
    print("QB_PACKAGE_COMPLETE", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    main(args.output, args.build)
