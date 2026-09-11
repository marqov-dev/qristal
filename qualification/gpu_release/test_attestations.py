import unittest

from attestations import check


class AttestationTests(unittest.TestCase):
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
