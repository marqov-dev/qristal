"""Package metadata inventory; no host paths, environment or credentials."""

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess

root = Path("/opt/marqov-qb")
packages = []
metadata_errors = []
for distribution in metadata.distributions():
    try:
        name, version = distribution.metadata.get("Name"), distribution.version
        if not name or not version:
            metadata_errors.append("distribution missing name or version")
        else:
            packages.append((name, version))
    except (OSError, ValueError, TypeError) as error:
        metadata_errors.append(type(error).__name__)
packages.sort()
licenses = []
scan_errors = []
for parent in (
    "/opt/nvidia",
    "/usr/local/cuda",
    "/usr/local/lib/python3.12/dist-packages/cuquantum",
):

    def record_error(error):
        scan_errors.append({"path": error.filename, "error": type(error).__name__})

    for directory, _, names in os.walk(parent, onerror=record_error):
        for name in names:
            file = Path(directory) / name
            if not any(
                word in name.lower()
                for word in ("license", "copyright", "notice", "eula")
            ):
                continue
            try:
                if (
                    file.is_file()
                    and not file.is_symlink()
                    and file.stat().st_size <= 2000000
                ):
                    licenses.append(
                        {
                            "path": str(file),
                            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                        }
                    )
            except OSError as error:
                record_error(error)
print(
    json.dumps(
        dict(
            python=platform.python_version(),
            architecture=platform.machine(),
            python_packages=packages,
            metadata_errors=metadata_errors,
            dpkg=subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"], timeout=30
            ).decode(),
            license_files=licenses,
            license_scan_errors=scan_errors,
            payload=json.loads((root / "payload.json").read_text()),
            observed_files={
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ("adapter.py", "fault_workload.py", "inventory.py")
            },
        ),
        sort_keys=True,
    )
)
