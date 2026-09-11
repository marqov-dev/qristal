"""Build a small derivative of the qualified NVIDIA image; no dependency solver."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"


def build(output):
    output.mkdir()
    files = {
        "adapter.py": ROOT / "gpu_adapter/adapter.py",
        "fault_workload.py": ROOT / "gpu_adapter/fault_workload.py",
        "inventory.py": HERE / "inventory.py",
    }
    lock = {
        "base": BASE,
        "files": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in files.items()
        },
    }
    with tempfile.TemporaryDirectory(prefix="qb-image-context-") as directory:
        context = Path(directory)
        for name, path in files.items():
            (context / name).write_bytes(path.read_bytes())
        (context / "payload.json").write_text(json.dumps(lock, sort_keys=True))
        (context / "Dockerfile").write_bytes((HERE / "Dockerfile").read_bytes())
        subprocess.run(
            [
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "--network",
                "none",
                "--iidfile",
                str(output / "image.id"),
                directory,
            ],
            check=True,
            timeout=1200,
        )
    identity = (output / "image.id").read_text().strip()
    inspection = json.loads(
        subprocess.check_output(["docker", "image", "inspect", identity], timeout=30)
    )[0]
    if (
        inspection["Architecture"] != "amd64"
        or inspection["Config"]["User"] != "65532:65532"
    ):
        raise RuntimeError("image_configuration")
    lock.update(
        image_id=identity,
        dockerfile_sha256=hashlib.sha256(
            (HERE / "Dockerfile").read_bytes()
        ).hexdigest(),
    )
    (output / "build.json").write_text(json.dumps(lock, indent=2) + "\n")
    print(identity)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
