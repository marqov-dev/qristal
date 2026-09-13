# Maintained simulation runtime distribution

We are packaging the useful public simulation capabilities in small, versioned
increments. A separate partner-preview milestone is unnecessary. Runtime delivery
can progress independently of Marqov's hosted execution integration.

## Available artifacts

[Catalog 2026-09-13.1](catalog.json) indexes existing observations, not a new binary
release. Its version identifies the catalog; it is not a simulator version.

| Artifact | Availability | Recorded scope |
| --- | --- | --- |
| Public CPU runtime, 9 September | Local image only; no registry pull URL | QPP/Aer CLI, ideal/noisy Bell examples, 43 installed functional fixtures, ten image test groups |
| Standalone CUDA-Q GPU runtime, 11 September | Private GHCR digest; registry access required | A10G, nvidia fp64/tensornet, twelve circuits, two negatives, three context faults and recovery |

CPU identity is a local configuration digest. GPU identity is a registry index
with separately checked platform-manifest/configuration bindings. They are not
interchangeable. Historical evidence is preserved without changing its original
publication status. Run the dependency-free catalog and retained GPU checks:

```sh
python3 -B qualification/distribution/check.py
```

This checks consistency with saved observations, not current registry access,
publisher authenticity or a fresh hardware run. The hashes bind selected records;
the existing GPU checker verifies the deeper provenance and native evidence.

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

## Next delivery increments

1. **CPU assembly:** capture verified installed-input hashes and build receipts;
   stage those inputs explicitly in a clean OCI recipe. Current checkout revisions
   cannot establish the provenance of old installed binaries. The legacy builder
   now labels them as observations and marks binary provenance unverified.
2. **CPU exact-artifact qualification:** bake the intended CLI/helpers; rerun the
   existing 43 fixtures and all advertised CLI/negative/isolation checks without
   source overlays. Record installed components, notices and build provenance.
   Publish only with exact registry identity and follow-up acquisition verification.
3. **GPU distribution:** reuse the already tested digest while payload is unchanged.
   Complete component redistribution/access review before public availability;
   source Apache-2.0 does not license the whole NVIDIA/OS image. Retain upstream
   notices and the existing SPDX/provenance records.
4. **Versioned iteration:** each binary change receives a new immutable digest,
   release notes and updated qualification evidence. Preserve prior failures and
   limits. Platform integration consumes this catalog later through its execution
   contract; it does not block standalone packaging.

Track packaging under platform issues #609, #640, #1585 and #1839; GPU follow-up
under #691. Conference evidence remains #2172/#1701. Decoder research is #2173
and proceeds separately. Do not close these wider issues on catalog delivery.

The [CPU staging increment](../cpu_package/README.md) now provides an explicit OCI
context and installed-byte receipt. [Real local staging evidence](../evidence/2026-09-13-cpu-staging/README.md)
records successful assembly of the context; the clean image build and native
qualification remain pending. This does not change the catalog's available artifacts.

The [first clean CPU OCI native build](../evidence/2026-09-13-cpu-oci/README.md)
subsequently passed the existing matrix with exact resource cleanup. Its image was
not exported from the disposable VM. Registry delivery, inventory export and the
corrected backend-negative test are the next increment; no new downloadable
artifact is implied.
