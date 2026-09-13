"""Replay named dependency-free qualification suites; never launch native compute."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SUITES = (
    ("source_artifact", (), "test_*.py"),
    ("core_build", (), "test_*.py"),
    ("source_build", (), "test_*.py"),
    ("source_provenance", (), "test_*.py"),
    ("cpu_release", (), "test_*.py"),
    ("cpu_package", (), "test_*.py"),
    ("distribution", (), "test_*.py"),
    ("full_decoder", (), "test_*.py"),
    ("full_decoder/cloud", (), "test_*.py"),
    ("conference/packet", (), "test_*.py"),
    ("gpu_release", (), "test_*.py"),
    ("gpu_package", (), "test_*.py"),
    ("gpu_adapter", ("accelerators", "runtime"), "test_*.py"),
    ("gpu_mapping", (), "test_*.py"),
    ("readout_sweep", (), "test_*.py"),
    ("readout_mitigation", (), "test_*.py"),
    ("readout_drift", (), "test_*.py"),
    ("readout_coverage", (), "test_*.py"),
    ("microvm", (), "test_check_evidence.py"),
    ("runtime", (), "test_readout_evidence.py"),
)


def main():
    for directory, extra, pattern in SUITES:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in (directory, *extra))
        print(f"Checking {directory}/{pattern}", flush=True)
        subprocess.run([sys.executable, "-B", "-m", "unittest", "discover",
                        "-s", str(ROOT / directory), "-p", pattern],
                       cwd=ROOT.parent, env=env, check=True, timeout=120)
    print("All selected offline suites passed; no native experiment performed.")


if __name__ == "__main__":
    main()
