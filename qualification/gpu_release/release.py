"""Stage exact release inputs and record immutable candidate identity."""

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IMAGE = "ghcr.io/marqov-dev/qristal-cudaq-gpu"
BASE = "nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage(output, record, revision):
    if not re.fullmatch("[a-f0-9]{40}", revision):
        raise ValueError("exact_source_revision_required")
    output.mkdir(parents=True)
    sources = {
        "adapter.py": ROOT / "gpu_adapter/adapter.py",
        "fault_workload.py": ROOT / "gpu_adapter/fault_workload.py",
        "inventory.py": ROOT / "gpu_package/inventory.py",
    }
    payload = {
        "base": BASE,
        "files": {name: sha(path.read_bytes()) for name, path in sources.items()},
    }
    content = {name: path.read_bytes() for name, path in sources.items()}
    content["payload.json"] = json.dumps(payload, sort_keys=True).encode()
    content["LICENSE.source"] = (ROOT.parent / "LICENSE").read_bytes()
    content["NOTICE.release.md"] = (HERE / "NOTICE.md").read_bytes()
    dockerfile = (ROOT / "gpu_package/Dockerfile").read_text()
    if dockerfile.splitlines()[0] != "FROM " + BASE:
        raise ValueError("base_recipe_changed")
    dockerfile += "\nCOPY --chmod=0555 LICENSE.source NOTICE.release.md /usr/share/licenses/marqov-cudaq/\n"
    dockerfile += 'LABEL org.opencontainers.image.source="https://github.com/marqov-dev/qristal"\n'
    dockerfile += f'LABEL org.opencontainers.image.revision="{revision}"\n'
    dockerfile += (
        'LABEL org.opencontainers.image.title="Marqov CUDA-Q workload candidate"\n'
    )
    content["Dockerfile"] = dockerfile.encode()
    for name, raw in content.items():
        (output / name).write_bytes(raw)
    record.write_text(
        json.dumps(
            {
                "source_revision": revision,
                "base_image": BASE,
                "context_files": {name: sha(raw) for name, raw in content.items()},
                "payload": payload,
            },
            indent=2,
        )
        + "\n"
    )


def receipt(context, digest, run, attempt):
    if not re.fullmatch("sha256:[a-f0-9]{64}", digest):
        raise ValueError("registry_digest_required")
    if not re.fullmatch("[a-f0-9]{40}", context["source_revision"]):
        raise ValueError("source_revision")
    if not str(run).isdigit() or not str(attempt).isdigit():
        raise ValueError("run_identity")
    return {
        "schema": "marqov.cudaq-release-candidate/v1",
        "image": IMAGE + "@" + digest,
        "source_revision": context["source_revision"],
        "workflow_run": f"https://github.com/marqov-dev/qristal/actions/runs/{run}/attempts/{attempt}",
        "context": context,
        "status": "published_candidate_not_gpu_qualified",
        "hosted_available": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage_parser = commands.add_parser("stage")
    stage_parser.add_argument("--output", type=Path, required=True)
    stage_parser.add_argument("--record", type=Path, required=True)
    stage_parser.add_argument("--revision", required=True)
    record_parser = commands.add_parser("record")
    record_parser.add_argument("--context", type=Path, required=True)
    record_parser.add_argument("--digest", required=True)
    record_parser.add_argument("--run", required=True)
    record_parser.add_argument("--attempt", required=True)
    record_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "stage":
        stage(args.output, args.record, args.revision)
    else:
        args.output.write_text(
            json.dumps(
                receipt(
                    json.loads(args.context.read_text()),
                    args.digest,
                    args.run,
                    args.attempt,
                ),
                indent=2,
            )
            + "\n"
        )
