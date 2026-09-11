import gzip
import hashlib
import json
from pathlib import Path
import unittest

from attestations import check


class AttestationTests(unittest.TestCase):
    def test_recovered_registry_documents(self):
        root = Path(__file__).resolve().parents[1] / "evidence/2026-09-11-gpu-release"
        recovery = json.loads((root / "recovery.json").read_text())
        for name, digest in recovery["files"].items():
            self.assertEqual(
                hashlib.sha256((root / name).read_bytes()).hexdigest(), digest
            )
        documents = {}
        for name, digest in recovery["expanded_files"].items():
            raw = gzip.decompress((root / (name + ".gz")).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            documents[name] = json.loads(raw)
        self.assertEqual(
            check(documents["sbom.json"], documents["provenance.json"]),
            {"spdx": "SPDX-2.3", "packages": 418, "slsa": "v1"},
        )
        release = json.loads((root / "reconstructed-release.json").read_text())
        self.assertEqual(
            release["image"].split("@")[1],
            "sha256:"
            + hashlib.sha256((root / "registry-index.json").read_bytes()).hexdigest(),
        )
        index = json.loads((root / "registry-index.json").read_text())
        self.assertEqual(
            index["manifests"][0]["digest"],
            "sha256:"
            + hashlib.sha256(
                (root / "platform-manifest.json").read_bytes()
            ).hexdigest(),
        )

    def setUp(self):
        self.sbom = {
            "SPDX": {"spdxVersion": "SPDX-2.3", "packages": [{"name": "fixture"}]}
        }
        self.v1 = {
            "SLSA": {
                "buildDefinition": {
                    "buildType": "https://github.com/moby/buildkit/blob/master/docs/attestations/slsa-definitions.md"
                },
                "runDetails": {},
            }
        }

    def test_current_v1(self):
        self.assertEqual(check(self.sbom, self.v1)["slsa"], "v1")

    def test_legacy_v02(self):
        self.assertEqual(
            check(
                self.sbom,
                {"SLSA": {"buildType": "https://mobyproject.org/buildkit@v1"}},
            )["slsa"],
            "v0.2",
        )

    def test_platform_wrapper(self):
        self.assertEqual(
            check({"linux/amd64": self.sbom}, {"linux/amd64": self.v1})["slsa"], "v1"
        )

    def test_missing_malformed_and_unknown_are_rejected(self):
        for value in (
            {},
            None,
            {"SLSA": {}},
            {"SLSA": {"buildDefinition": None}},
            {"SLSA": {"buildType": "other"}},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check(self.sbom, value)

    def test_ambiguous_documents_rejected(self):
        with self.assertRaises(ValueError):
            check(self.sbom, {**self.v1, "linux/amd64": self.v1})

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            check({"SPDX": {"spdxVersion": "SPDX-2.3", "packages": []}}, self.v1)
