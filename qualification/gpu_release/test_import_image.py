import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from import_image import archive_config, bind_release, digest, validate_loaded


class ImportTests(unittest.TestCase):
    def test_real_manifest_chain_and_mutations(self):
        root = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-release"
        release = json.loads((root / "reconstructed-release.json").read_text())
        index = (root / "registry-index.json").read_bytes()
        manifest = (root / "platform-manifest.json").read_bytes()
        self.assertEqual(
            bind_release(release, index, manifest),
            "sha256:9c3e6d3d51c5fc4cd04766257cc7194e65ddf458f47d3bf7beb8ffc15676031b",
        )
        for changed_index, changed_manifest in (
            (index + b" ", manifest),
            (index, manifest + b" "),
        ):
            with self.assertRaises(ValueError):
                bind_release(release, changed_index, changed_manifest)

    def test_archive_configuration_must_match_registry(self):
        raw = b'{"rootfs":{"diff_ids":[]}}'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.tar"
            with tarfile.open(path, "w") as archive:
                for name, data in (
                    ("config.json", raw),
                    (
                        "manifest.json",
                        json.dumps(
                            [
                                {
                                    "Config": "config.json",
                                    "RepoTags": ["fixture:only"],
                                    "Layers": [],
                                }
                            ]
                        ).encode(),
                    ),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            self.assertEqual(archive_config(path, digest(raw))[0], "fixture:only")
            with self.assertRaises(ValueError):
                archive_config(path, digest(b"other"))

    def test_loaded_identity_layers_user_revision(self):
        config = {"rootfs": {"diff_ids": ["sha256:layer"]}}
        loaded = {
            "Id": "sha256:config",
            "Architecture": "amd64",
            "Os": "linux",
            "Config": {
                "User": "65532:65532",
                "Labels": {"org.opencontainers.image.revision": "revision"},
            },
            "RootFS": {"Layers": ["sha256:layer"]},
        }
        validate_loaded(loaded, config, "revision", "sha256:config")
        for field, value in (
            ("Id", "sha256:other"),
            ("RootFS", {"Layers": []}),
            ("Architecture", "arm64"),
            ("Config", {"User": "root", "Labels": {}}),
        ):
            bad = copy.deepcopy(loaded)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_loaded(bad, config, "revision", "sha256:config")
