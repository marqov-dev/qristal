"""Run only on an authorized disposable NVIDIA host; image must already be pulled."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bounded_process import capture

IMAGE = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"


def docker(*args):
    return subprocess.check_output(
        ["docker", *args], timeout=30, stderr=subprocess.PIPE
    )


def main(output):
    output.mkdir(mode=0o700)
    docker("image", "inspect", IMAGE)
    hardware = (
        subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            timeout=15,
        )
        .decode()
        .strip()
    )
    records = []
    for target in ("nvidia", "tensornet"):
        name = "qb-gpu-" + uuid.uuid4().hex

        def owned():
            return (
                docker(
                    "ps",
                    "-aq",
                    "--filter",
                    f"name=^/{name}$",
                    "--filter",
                    f"label=qb.gpu={name}",
                )
                .decode()
                .split()
            )

        try:
            docker(
                "create",
                "--pull",
                "never",
                "--name",
                name,
                "--label",
                f"qb.gpu={name}",
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
                "--mount",
                f"type=bind,source={HERE},target=/probe,readonly",
                "--entrypoint",
                "python3",
                IMAGE,
                "-B",
                "/probe/gpu_probe.py",
                target,
            )
            code, stdout, stderr = capture(
                ["docker", "start", "-a", name],
                timeout=300,
                stdout_limit=131072,
                stderr_limit=16384,
            )
            (output / (target + ".stdout")).write_bytes(stdout)
            (output / (target + ".stderr")).write_bytes(stderr)
            if code:
                raise RuntimeError(
                    f"{target}_failed exit={code}: "
                    + stderr[-1000:].decode(errors="replace")
                )
            lines = [
                line.removeprefix(b"QB_GPU_RESULT ")
                for line in stdout.splitlines()
                if line.startswith(b"QB_GPU_RESULT ")
            ]
            if len(lines) != 1:
                raise RuntimeError("missing_result")
            result = json.loads(lines[0])
            if result["target"] != target or len(result["records"]) != 6:
                raise RuntimeError("invalid_result")
            records.append(result)
        finally:
            for identity in owned():
                docker("rm", "-f", identity)
            if owned():
                raise RuntimeError("cleanup_failed")
    report = {
        "hardware": hardware,
        "image": IMAGE,
        "results": records,
        "owned_containers_absent": True,
        "sources": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in HERE.glob("*.py")
        },
    }
    (output / "result.json").write_text(json.dumps(report, sort_keys=True) + "\n")
    print("QB_GPU_PROOF " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    main(p.parse_args().output)
