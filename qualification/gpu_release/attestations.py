"""Check extracted BuildKit attestation shapes; not publisher authentication."""

import argparse
import json
from pathlib import Path


def document(value, key):
    if not isinstance(value, dict):
        raise ValueError("attestation_object_required")
    direct = value.get(key)
    platform = value.get("linux/amd64", {})
    if not isinstance(platform, dict):
        raise ValueError("attestation_platform_object_required")
    nested = platform.get(key)
    if direct is not None and nested is not None:
        raise ValueError("ambiguous_attestation")
    result = direct if direct is not None else nested
    if not isinstance(result, dict):
        raise ValueError("attestation_missing: " + key)
    return result


def check(sbom, provenance):
    spdx = document(sbom, "SPDX")
    if spdx.get("spdxVersion") != "SPDX-2.3" or not spdx.get("packages"):
        raise ValueError("spdx_packages_required")
    slsa = document(provenance, "SLSA")
    if "buildDefinition" in slsa:
        definition = slsa["buildDefinition"]
        if not isinstance(definition, dict) or definition.get("buildType") != (
            "https://github.com/moby/buildkit/blob/master/docs/attestations/slsa-definitions.md"
        ):
            raise ValueError("slsa_v1_build_type")
        if not isinstance(slsa.get("runDetails"), dict):
            raise ValueError("slsa_v1_run_details")
        version = "v1"
    elif slsa.get("buildType") == "https://mobyproject.org/buildkit@v1":
        version = "v0.2"
    else:
        raise ValueError("unsupported_buildkit_provenance")
    return {
        "spdx": spdx["spdxVersion"],
        "packages": len(spdx["packages"]),
        "slsa": version,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            check(
                json.loads((args.directory / "sbom.json").read_text()),
                json.loads((args.directory / "provenance.json").read_text()),
            )
        )
    )
