"""Replay exact retained logs; does not verify the omitted installation archive."""
import importlib.util
import json
from pathlib import Path
root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("native_checker", root.parents[1] / "core_native/check_result.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
report = json.loads((root / "recovered-full-report.json").read_text())["result"]
result = checker.classify(report, root / "protocol.json", root / "stage-logs.tar.gz")
print(json.dumps(result, indent=2))
if result.get("native_passed") is not True:
    raise SystemExit(1)
