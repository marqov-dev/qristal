# Maintained simulation runtime distribution

We are packaging the useful public simulation capabilities in small, versioned
increments. A separate partner-preview milestone is unnecessary. Runtime delivery
can progress independently of Marqov's hosted execution integration.

## Available artifacts

[Catalog 2026-09-13.2](catalog.json) indexes historical observations and authenticated registry candidates. Its version identifies the catalog; it is not a simulator version.

| Artifact | Availability | Recorded scope |
| --- | --- | --- |
| Historical public CPU runtime, 9 September | Local image only; no registry pull URL | QPP/Aer CLI, ideal/noisy Bell examples, 43 installed functional fixtures, ten image test groups |
| Maintained CPU candidate, 13 September | Private GHCR digest; registry access required |43 functional fixtures, corrected backend rejection, acquired image inventory |
| Standalone CUDA-Q GPU runtime, 11 September | Private GHCR digest; registry access required | A10G, nvidia fp64/tensornet, twelve circuits, two negatives, three context faults and recovery |

The historical CPU identity is a local configuration digest. Both published
CPU/GPU identities are registry indexes with separately checked platform-manifest
and configuration bindings. They are not
interchangeable. Historical evidence is preserved without changing its original
publication status. Run the dependency-free catalog and retained GPU checks:

```sh
python3 -B qualification/distribution/check.py
```

This checks consistency with saved observations, not current registry access,
publisher authenticity or a fresh hardware run. The hashes bind selected records;
the existing GPU and CPU checkers replay the deeper identity and native evidence.

## Using what exists

For an operator who already has the exact CPU image locally, the recorded
[image test commands](../evidence/2026-09-09-runtime-image/image-tests.json)
provide the tested invocations, resource limits and expected exit codes. Start
with `--capabilities`, then the bundled `/checks/bell.qasm` example. Do not treat
the local digest as a remotely downloadable image. The current
[CPU recipe](../runtime/README.md) requires installed dependency trees; it is not
yet a turnkey clean-source release build.

For GPU acquisition and execution, follow the existing
[registry acquisition guide](../gpu_release/README.md) and
[packaged native qualification guide](../gpu_package/README.md). Use the catalog's
immutable digest, not a moving tag. The tested host was Linux amd64 with an NVIDIA
A10G; Docker GPU support, a compatible host driver and container toolkit are
required. Registry credentials belong on the trusted acquisition machine, not in
the workload. The qualification harness requires an isolated GPU host.

The conference noise, mitigation and drift experiments also use later source
helpers. Their overlay evidence does not mean those helpers are baked into the
9 September CPU image. Full Decoder, the historical Core GPU bridge, TNQVM,
commercial Emulator and internal vQPU are outside this catalog. Neither image is
thereby admitted to hosted execution. See the [current demonstration scope](../conference/CURRENT.md).

## Current CPU candidate

The [published CPU result](../evidence/2026-09-13-cpu-published/README.md) records
successful prepublication and acquired-digest matrices. On a trusted Linux amd64
Docker host with registry access, authenticate through your normal GHCR login and
pull the exact candidate:

```sh
CPU_IMAGE=ghcr.io/marqov-dev/qristal-cpu@sha256:c500987ef91ab0e0d3dd32ea75436785308ae1603c221762291d9c13dff431c5
docker pull "$CPU_IMAGE"
docker run --rm --pull never --platform linux/amd64 --network none \
  --cpus 2 --memory 4g --memory-swap 4g --pids-limit 256 --read-only \
  --tmpfs /tmp:rw,exec,size=128m --cap-drop ALL --security-opt no-new-privileges \
  "$CPU_IMAGE" --qasm /checks/bell.qasm
```

No GPU is needed. This is a restricted simulation CLI, not a general Python
notebook or hosted job protocol. Existing registry authorization is required;
this guide does not grant access. The package/source licenses and component
notices remain distinct from public redistribution clearance.

## Remaining delivery increments

1. Bind installed bytes to controlled source acquisition, build and install
   receipts. The first candidate still labels original binary build provenance
   unverified; packaging source revisions do not fill that gap.
2. Review component redistribution and public availability using retained
   inventories/notices. Keep the draft input unpublished until deliberately
   replaced or retired; do not turn it into a supported release accidentally.
3. Preserve prior artifact identities and verification contracts when updating
   matrix, payload or dependencies; rerun native acquired-digest checks for each
   changed binary. Retain failures and limits.
4. Keep platform integration on its execution contract and independent schedule.
   Full Decoder, original GPU bridge and broader noise/scale are separate gates.

Packaging tracking remains #609, #640, #1585 and #1839; GPU follow-up #691;
conference #2172/#1701; Decoder #2173. This candidate does not complete those
broader issues or imply partnership, public endorsement or hosted admission.
