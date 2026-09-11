"""Import a digest-bound Docker archive on a disposable qualification host.

No registry login, network acquisition, build or workload execution occurs here.
The archive and expected release records come from the trusted acquisition step.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def file_digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def bind_release(release, index_raw, manifest_raw):
    if release["image"] != "ghcr.io/marqov-dev/qristal-cudaq-gpu@" + digest(index_raw):
        raise ValueError("registry_index_binding")
    index = json.loads(index_raw)
    platforms = [
        m
        for m in index["manifests"]
        if m.get("platform") == {"os": "linux", "architecture": "amd64"}
    ]
    if len(platforms) != 1 or platforms[0]["digest"] != digest(manifest_raw):
        raise ValueError("platform_manifest_binding")
    return json.loads(manifest_raw)["config"]["digest"]


def archive_config(path, config_digest):
    with tarfile.open(path) as archive:

        def read(name):
            entry = archive.getmember(name)
            if not entry.isfile() or entry.size > 1024 * 1024:
                raise ValueError("archive_metadata_bounds")
            return archive.extractfile(entry).read()

        manifest = json.loads(read("manifest.json"))
        if len(manifest) != 1 or len(manifest[0].get("RepoTags", [])) != 1:
            raise ValueError("one_tagged_image_required")
        raw = read(manifest[0]["Config"])
        if digest(raw) != config_digest:
            raise ValueError("archive_configuration_binding")
        return manifest[0]["RepoTags"][0], json.loads(raw)


def validate_loaded(loaded, config, revision, config_digest):
    if (
        loaded["Id"] != config_digest
        or loaded["Architecture"] != "amd64"
        or loaded["Os"] != "linux"
        or loaded["Config"]["User"] != "65532:65532"
        or loaded["RootFS"]["Layers"] != config["rootfs"]["diff_ids"]
        or loaded["Config"].get("Labels", {}).get("org.opencontainers.image.revision")
        != revision
    ):
        raise ValueError("loaded_configuration_binding")


def main(archive, expected_archive, bundle, output):
    if output.exists():
        raise ValueError("new_output_required")
    release = json.loads((bundle / "reconstructed-release.json").read_text())
    index_raw = (bundle / "registry-index.json").read_bytes()
    manifest_raw = (bundle / "platform-manifest.json").read_bytes()
    config_digest = bind_release(release, index_raw, manifest_raw)
    if file_digest(archive) != expected_archive:
        raise ValueError("archive_checksum")
    tag, config = archive_config(archive, config_digest)
    subprocess.run(
        ["docker", "load", "--input", str(archive)], check=True, timeout=1200
    )
    loaded = json.loads(
        subprocess.check_output(["docker", "image", "inspect", tag], timeout=30)
    )[0]
    validate_loaded(loaded, config, release["source_revision"], config_digest)
    lock = {
        "image_id": loaded["Id"],
        "base": release["context"]["base_image"],
        "files": release["context"]["payload"]["files"],
        "dockerfile_sha256": release["context"]["context_files"]["Dockerfile"],
        "release_binding": {
            "registry_image": release["image"],
            "platform_manifest": digest(manifest_raw),
            "configuration": config_digest,
            "archive_sha256": expected_archive,
            "source_revision": release["source_revision"],
            "transport": "private single-object transfer; no registry credential on host",
        },
    }
    output.write_text(json.dumps(lock, indent=2) + "\n")
    print("QB_RELEASE_IMPORT_VERIFIED " + loaded["Id"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.archive, args.archive_sha256, args.bundle, args.output)
