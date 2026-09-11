"""Verify saved published-image observations, not hosted execution authority."""

import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

from attestations import check as check_attestations, document
from import_image import bind_release, digest, load_release

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "package_checker", HERE.parent / "gpu_package/check_evidence.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def verify(report, bundle, transfer):
    release = load_release(bundle)
    index = (bundle / "registry-index.json").read_bytes()
    manifest = (bundle / "platform-manifest.json").read_bytes()
    config = bind_release(release, index, manifest)
    package.verify(
        report, expected_recipe_sha256=release["context"]["context_files"]["Dockerfile"]
    )
    build = report["build"]
    expected = {
        "registry_image": release["image"],
        "platform_manifest": digest(manifest),
        "configuration": config,
        "archive_sha256": transfer["archive_sha256"],
        "source_revision": release["source_revision"],
        "transport": "private single-object transfer; no registry credential on host",
    }
    if build["release_binding"] != expected:
        raise ValueError("release_transport_binding")
    if build["image_id"] not in (config, digest(index), digest(manifest)):
        raise ValueError("published_image_identity")
    if (
        transfer["registry_image"] != release["image"]
        or transfer["configuration"] != config
        or transfer["source_revision"] != release["source_revision"]
    ):
        raise ValueError("acquisition_binding")


def verify_retained(root):
    intent = json.loads((root / "native-intent.json").read_text())
    for name, expected in intent["operator_scripts"].items():
        if (
            hashlib.sha256((root / "operator" / name).read_bytes()).hexdigest()
            != expected
        ):
            raise ValueError("operator_script_binding")
    for name, expected in json.loads(
        (root / "recovery-scripts.json").read_text()
    ).items():
        if (
            hashlib.sha256((root / "operator" / name).read_bytes()).hexdigest()
            != expected
        ):
            raise ValueError("recovery_script_binding")
    bundle = root / "release"
    records = json.loads((bundle / "manifest.json").read_text())["records"]
    if set(records) != {
        "release.json",
        "context.json",
        "registry-index.json",
        "platform-manifest.json",
        "build-metadata.json",
        "sbom.json",
        "provenance.json",
    }:
        raise ValueError("release_record_set")
    documents = {}
    for name, record in records.items():
        stored = (bundle / record["stored_file"]).read_bytes()
        raw = (
            gzip.decompress(stored) if record["stored_file"].endswith(".gz") else stored
        )
        if (
            hashlib.sha256(stored).hexdigest() != record["stored_sha256"]
            or hashlib.sha256(raw).hexdigest() != record["sha256"]
            or len(raw) != record["bytes"]
        ):
            raise ValueError("retained_release_bytes")
        documents[name] = json.loads(raw)
    check_attestations(documents["sbom.json"], documents["provenance.json"])
    release = documents["release.json"]
    slsa = document(documents["provenance.json"], "SLSA")
    args = slsa["buildDefinition"]["externalParameters"]["request"]["root"]["request"][
        "args"
    ]
    if (
        documents["context.json"] != release["context"]
        or documents["build-metadata.json"]["containerimage.digest"]
        != release["image"].split("@", 1)[1]
        or slsa["runDetails"]["builder"]["id"] != release["workflow_run"]
        or args["vcs:revision"] != release["source_revision"]
        or args["vcs:source"] != "https://github.com/marqov-dev/qristal"
    ):
        raise ValueError("release_record_agreement")
    for name, expected_hash in json.loads(
        (root / "source-hashes.json").read_text()
    ).items():
        if name.startswith("qualification/"):
            path = HERE.parents[1] / name
        elif name.startswith("bundle/"):
            path = bundle / name.removeprefix("bundle/")
        elif name == "transfer.json":
            path = root / name
        else:
            raise ValueError("unexpected_staged_file")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("staged_source_binding")


def main(root):
    verify_retained(root)
    report = json.loads((root / "result.json").read_text())
    verify(report, root / "release", json.loads((root / "transfer.json").read_text()))
    spec = importlib.util.spec_from_file_location(
        "console_recovery", HERE.parent / "gpu_package/console.py"
    )
    console = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(console)
    recovered, complete, truncated = console.recover(
        (root / "console-observed.txt").read_text()
    )
    if recovered != report or complete != (root / "console-chunks.txt").read_text():
        raise ValueError("console_binding")
    if (
        truncated
        != json.loads((root / "console-recovery.json").read_text())[
            "discarded_truncated_nonfinal_fragments"
        ]
    ):
        raise ValueError("console_recovery_binding")
    cleanup = json.loads((root / "cleanup.json").read_text())
    if not all(
        cleanup.get(key) is True
        for key in (
            "instance_absent",
            "volumes_absent",
            "security_group_deleted",
            "security_group_absent",
        )
    ):
        raise ValueError("host_cleanup")
    volume_check = cleanup["volume_verification"]
    launch = json.loads((root / "launch-audit.json").read_text())[0]

    def parse_time(value):
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))

    if (
        volume_check["matching_volumes"] != []
        or volume_check["region"] != "us-east-1"
        or launch["instance_id"] != cleanup["instance_id"]
        or not parse_time(volume_check["from_inclusive"])
        <= parse_time(launch["event_time"])
        <= parse_time(volume_check["to_inclusive"])
    ):
        raise ValueError("launch_window_cleanup")
    if (
        json.loads((root / "transfer-cleanup.json").read_text()).get("bucket_absent")
        is not True
    ):
        raise ValueError("transfer_cleanup")
    print(
        "PASS: published identity, transfer, 12 circuits, 2 negatives, 3 faults, recovery and cleanup audit (volume-window fallback)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    main(parser.parse_args().directory)
