"""Verify retained synthetic counts and replay the summary; no random sampling."""
import hashlib
import json
from pathlib import Path
from study import ROOT, SOURCE, analyze

EVIDENCE=ROOT.parent/"evidence"/"2026-09-12-readout-coverage"


def check(path=EVIDENCE):
    manifest=json.loads((path/"manifest.json").read_text())
    if manifest["kind"] != "synthetic-multinomial-coverage" or manifest["native_execution"] is not False:
        raise ValueError("execution_kind")
    if set(manifest["files"]) != {"counts.json","summary.json"}:
        raise ValueError("file_set")
    for name, digest in manifest["files"].items():
        if hashlib.sha256((path/name).read_bytes()).hexdigest() != digest:
            raise ValueError("file_hash")
    for source,key in ((ROOT/"study.py","source_sha256"),(SOURCE,"estimator_sha256")):
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest[key]:
            raise ValueError("source_hash")
    if analyze(json.loads((path/"counts.json").read_text())) != json.loads((path/"summary.json").read_text()):
        raise ValueError("analysis")
    return manifest


if __name__ == "__main__":
    check()
    print("Retained synthetic evidence verified; no native execution.")
