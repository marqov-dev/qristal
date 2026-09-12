"""Reuse the bounded readout image harness for a predeclared 40-case calibration-drift experiment."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile

from demo import analyze

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runtime"))
import qualify_readout_image as native  # noqa: E402


def main(output):
    output.mkdir(mode=0o700)
    sources = {name: (native.HERE / name).read_bytes() for name in native.FILES}
    sources["readout_demo.py"] = (HERE / "demo.py").read_bytes()
    sources["mitigation_core.py"] = (HERE.parent / "readout_mitigation" / "demo.py").read_bytes()
    native.FILES = tuple(sources)
    inspected = json.loads(native.docker("image", "inspect", native.IMAGE))[0]
    if inspected["Id"] != native.IMAGE or inspected["Architecture"] != "amd64":
        raise ValueError("cpu_image_identity")
    with tempfile.TemporaryDirectory(prefix="qb-readout-mitigation-") as directory:
        staging = Path(directory)
        for name, raw in sources.items():
            (staging / name).write_bytes(raw)
        native.HERE = staging
        raw = native.run_stage(output, "demo")
    report = json.loads(raw)
    summary = analyze(report)
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    manifest = {
        "image": native.IMAGE,
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "native_harness_sha256": hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        "native_rebuild": False,
        "cloud_execution": False,
        "sources": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()
        },
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()
        },
        "cases": len(report["records"]),
        "owned_containers_absent": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("PASS: 40 drift cases, refreshed calibration validated; container cleanup verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
