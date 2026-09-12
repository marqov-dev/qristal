"""Replay measured calibration and held-out results without Docker or Qristal."""
import hashlib
import json
from pathlib import Path

from demo import analyze

IMAGE = "sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44"


def check(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    required = {"result.json", "analysis.json", "demo.stdout", "demo.stderr",
                "demo-intent.json", "demo-cleanup.json"}
    if (not required <= set(manifest["files"]) or manifest["image"] != IMAGE
            or manifest["cases"] != 40 or manifest["native_rebuild"]
            or manifest["cloud_execution"] or not manifest["owned_containers_absent"]):
        raise ValueError("evidence_profile")
    for name, digest in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("evidence_path")
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("evidence_hash")
    if manifest["sources"]["readout_demo.py"] != hashlib.sha256(
            (Path(__file__).parent / "demo.py").read_bytes()).hexdigest():
        raise ValueError("source_binding")
    core_source = Path(__file__).parent.parent / "readout_mitigation" / "demo.py"
    if manifest["sources"]["mitigation_core.py"] != hashlib.sha256(core_source.read_bytes()).hexdigest():
        raise ValueError("estimator_binding")
    intent = json.loads((root / "demo-intent.json").read_text())
    cleanup = json.loads((root / "demo-cleanup.json").read_text())
    if (intent["image"] != IMAGE or intent["name"] != cleanup["name"]
            or cleanup["absent"] is not True):
        raise ValueError("cleanup")
    report = json.loads((root / "result.json").read_text())
    if json.loads((root / "demo.stdout").read_text()) != report or (root / "demo.stderr").read_bytes():
        raise ValueError("native_output")
    summary = analyze(report)
    if summary != json.loads((root / "analysis.json").read_text()):
        raise ValueError("analysis_changed")
    return summary


if __name__ == "__main__":
    import sys
    print(json.dumps(check(sys.argv[1])["settings"], indent=2))
