"""Package metadata inventory; no host paths, environment or credentials."""

import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess

root = Path("/opt/marqov-qb")
packages = sorted((d.metadata["Name"], d.version) for d in metadata.distributions())
licenses = []
for parent in (
    "/opt/nvidia",
    "/usr/local/cuda",
    "/usr/local/lib/python3.12/dist-packages/cuquantum",
):
    path = Path(parent)
    if path.exists():
        for file in path.rglob("*"):
            if (
                file.is_file()
                and not file.is_symlink()
                and any(
                    word in file.name.lower()
                    for word in ("license", "copyright", "notice", "eula")
                )
            ):
                if file.stat().st_size <= 2000000:
                    licenses.append(
                        {
                            "path": str(file),
                            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                        }
                    )
print(
    json.dumps(
        dict(
            python=platform.python_version(),
            architecture=platform.machine(),
            python_packages=packages,
            dpkg=subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"], timeout=30
            ).decode(),
            license_files=licenses,
            payload=json.loads((root / "payload.json").read_text()),
            observed_files={
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ("adapter.py", "fault_workload.py", "inventory.py")
            },
        ),
        sort_keys=True,
    )
)
