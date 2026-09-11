"""One authorized disposable GPU host; no hosted platform authority or identity."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from adapter import IMAGE
from bounded_process import capture, ProcessError
from fixtures import cases, check


def docker(*args):
    return subprocess.check_output(
        ["docker", *args], timeout=30, stderr=subprocess.PIPE
    ).decode()


def gpu_pids():
    raw = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        timeout=15,
    ).decode()
    return sorted(int(p) for p in raw.split() if p.isdigit())


def empty_gpu():
    for _ in range(20):
        if not gpu_pids():
            return
        time.sleep(0.5)
    raise RuntimeError("gpu_processes_remain")


def create(name, entry):
    docker(
        "create",
        "--pull",
        "never",
        "--name",
        name,
        "--label",
        "qb.adapter=" + name,
        "--gpus",
        "all",
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
        "--env",
        "HOME=/tmp",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--log-opt",
        "max-size=1m",
        "--log-opt",
        "max-file=1",
        "--mount",
        f"type=bind,source={HERE},target=/probe,readonly",
        "--entrypoint",
        "python3",
        IMAGE,
        "-B",
        *entry,
    )


def remove(name):
    ids = docker(
        "ps",
        "-aq",
        "--filter",
        f"name=^/{name}$",
        "--filter",
        f"label=qb.adapter={name}",
    ).split()
    for identity in ids:
        docker("rm", "-f", identity)
    if docker("ps", "-aq", "--filter", f"name=^/{name}$").strip():
        raise RuntimeError("container_remains")
    empty_gpu()


def run_case(target, case, inputs):
    raw = json.dumps(
        dict(
            schema="qristal.cudaq-circuit/v1",
            target=target,
            qubits=case["qubits"],
            shots=16384,
            seed=42,
            gates=case["gates"],
        ),
        sort_keys=True,
    ).encode()
    path = inputs / f"{target}-{case['name']}.json"
    path.write_bytes(raw)
    path.chmod(0o644)
    digest = hashlib.sha256(raw).hexdigest()
    name = "qb-adapter-" + uuid.uuid4().hex
    empty_gpu()
    try:
        create(
            name,
            ["/probe/adapter.py", f"/probe/inputs/{path.name}", "--sha256", digest],
        )
        code, stdout, stderr = capture(
            ["docker", "start", "-a", name],
            timeout=120,
            stdout_limit=131072,
            stderr_limit=16384,
        )
        if code:
            raise RuntimeError(
                f"adapter_exit_{code}: " + stderr[-1000:].decode(errors="replace")
            )
        result = json.loads(stdout)
        if (
            result["input_sha256"] != digest
            or result["target"] != target
            or result["schema"] != "qristal.cudaq-candidate/v1"
            or result["runtime_image"] != IMAGE
        ):
            raise RuntimeError("candidate_binding")
        check(result["counts"], case)
        state = json.loads(docker("inspect", name))[0]["State"]
        if state["Running"] or state["ExitCode"] != 0:
            raise RuntimeError("not_stopped")
        return dict(
            case=case["name"],
            artifact=json.loads(raw),
            candidate=result,
            exit_code=state["ExitCode"],
            stopped_observed=True,
        )
    finally:
        remove(name)


def fault(mode):
    name = "qb-adapter-" + uuid.uuid4().hex
    empty_gpu()
    try:
        create(name, ["/probe/fault_workload.py", mode])
        docker("start", name)
        deadline = time.monotonic() + 60
        while True:
            try:
                docker("exec", name, "test", "-f", "/tmp/gpu-ready")
                break
            except subprocess.CalledProcessError:
                if time.monotonic() > deadline:
                    raise RuntimeError("gpu_fixture_not_ready")
                time.sleep(0.5)
        processes = gpu_pids()
        top = docker("top", name, "-eo", "pid").splitlines()[1:]
        container_pids = {int(p.strip()) for p in top if p.strip().isdigit()}
        if not set(processes) & container_pids:
            raise RuntimeError("owned_gpu_context_not_observed")
        if mode == "cancel":
            docker("kill", "--signal", "KILL", name)
            outcome = "requested_kill"
        else:
            if mode == "overflow":
                docker("exec", name, "touch", "/tmp/go")
            try:
                capture(
                    ["docker", "attach", name],
                    timeout=3,
                    stdout_limit=4096,
                    stderr_limit=4096,
                )
            except ProcessError as exc:
                outcome = str(exc)
            else:
                raise RuntimeError("fault_did_not_trigger")
            expected = (
                "process_timeout" if mode == "timeout" else "process_output_limit"
            )
            if outcome != expected:
                raise RuntimeError("wrong_fault_" + outcome)
            docker("kill", "--signal", "KILL", name)
        state = json.loads(docker("inspect", name))[0]["State"]
        if state["Running"] or state["ExitCode"] != 137:
            raise RuntimeError("kill_not_observed")
        return dict(
            mode=mode,
            owned_gpu_context_observed=True,
            outcome=outcome,
            exit_code=137,
            stopped_observed=True,
        )
    finally:
        remove(name)


def main(output):
    output.mkdir(mode=0o700)
    inputs = HERE / "inputs"
    inputs.mkdir(mode=0o755)
    docker("image", "inspect", IMAGE)
    records = [
        run_case(target, case, inputs)
        for target in ("nvidia", "tensornet")
        for case in cases()
    ]
    faults = [fault(mode) for mode in ("cancel", "timeout", "overflow")]
    recovery = run_case("nvidia", cases()[0], inputs)
    report = dict(
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
        image=IMAGE,
        scope="standalone workload and single-host lifecycle qualification",
        records=records,
        faults=faults,
        recovery=recovery,
        owned_containers_absent=True,
        gpu_processes_absent=True,
        sources={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in HERE.glob("*.py")
        },
    )
    raw = json.dumps(report, sort_keys=True).encode()
    (output / "result.json").write_bytes(raw)
    encoded = base64.b64encode(zlib.compress(raw)).decode()
    # Short independently indexed chunks avoid long-line console timestamp corruption.
    parts = [encoded[i : i + 160] for i in range(0, len(encoded), 160)]
    digest = hashlib.sha256(raw).hexdigest()
    for index, part in enumerate(parts):
        print(f"QB_ADAPTER_CHUNK {digest} {index} {len(parts)} {part}", flush=True)
    print("QB_ADAPTER_COMPLETE", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output)
