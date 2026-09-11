"""Local MPS/density feasibility using the existing image; no build or downloads."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runtime"))
from bounded_process import capture

IMAGE = "sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44"


def main(output):
    output.mkdir(mode=0o700)
    name = "qristal-cpu-methods-" + uuid.uuid4().hex

    def docker(*args):
        return subprocess.check_output(
            ["docker", *args], timeout=30, stderr=subprocess.PIPE
        )

    def owned():
        return (
            docker(
                "ps",
                "-aq",
                "--filter",
                f"name=^/{name}$",
                "--filter",
                f"label=qristal.cpu-methods={name}",
            )
            .decode()
            .split()
        )

    sources = {n: (HERE / n).read_text() for n in ("fixtures.py", "cpu_probe.py")}
    code = "import pathlib,sys,runpy\nsources=" + repr(sources) + "\n"
    code += "base=pathlib.Path('/tmp/cpu-methods');base.mkdir()\n"
    code += "for name,source in sources.items(): (base/name).write_text(source)\n"
    code += "sys.path.insert(0,str(base))\nrunpy.run_path(str(base/'cpu_probe.py'),run_name='__main__')\n"
    (output / "intent.json").write_text(json.dumps({"container": name, "image": IMAGE}))
    try:
        docker("image", "inspect", IMAGE)
        docker(
            "create",
            "--pull",
            "never",
            "--name",
            name,
            "--label",
            f"qristal.cpu-methods={name}",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--cpus",
            "2",
            "--memory",
            "4g",
            "--memory-swap",
            "4g",
            "--pids-limit",
            "256",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,exec,size=128m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65532:65532",
            "--entrypoint",
            "python3",
            IMAGE,
            "-B",
            "-c",
            code,
        )
        exit_code, stdout, stderr = capture(
            ["docker", "start", "-a", name],
            timeout=240,
            stdout_limit=131072,
            stderr_limit=8192,
        )
        (output / "cpu.stdout").write_bytes(stdout)
        (output / "cpu.stderr").write_bytes(stderr)
        if exit_code or stderr:
            raise RuntimeError("cpu_probe_failed")
        report = json.loads(stdout)
        if len(report["records"]) != 18:
            raise ValueError("incomplete_matrix")
    finally:
        for identity in owned():
            docker("rm", "-f", identity)
        if owned():
            raise RuntimeError("cleanup_failed")
        (output / "cleanup.json").write_text(
            json.dumps({"container": name, "absent": True})
        )
    manifest = {
        "image": IMAGE,
        "source_base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE)
        .decode()
        .strip(),
        "sources": {
            n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
            for n in ("fixtures.py", "cpu_probe.py", "qualify_cpu.py")
        },
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print("PASS: 18 explicit CPU method cases; owned container absent")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output)
