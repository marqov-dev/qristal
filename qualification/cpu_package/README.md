# CPU runtime assembly from captured installed inputs

This replaces the mutable-container/`docker commit` assembly step with an explicit
OCI build context. It does not compile the dependencies, establish their original
build provenance, publish an image or qualify a new runtime.

## Prepare and verify a context

Use the isolated workspace described in the [installed runtime guide](../installed/README.md).
The input allowlist in `stage.py` includes installed native libraries/plugins,
the two separate Python environments, installed fixtures, the decoder smoke
consumer, collected component notices, and the current CPU CLI/capability files.
It adds this repository's source license explicitly. The component notice tree
must already have been collected; its inclusion is not a complete license audit.

```sh
python3 -B qualification/cpu_package/stage.py capture \
  --workspace /path/to/isolated-workspace --output /tmp/cpu-inputs.json
python3 -B qualification/cpu_package/stage.py stage \
  --workspace /path/to/isolated-workspace --receipt /tmp/cpu-inputs.json \
  --output /tmp/cpu-context
python3 -B qualification/cpu_package/stage.py verify --output /tmp/cpu-context
```

Both output names must be new. The context must be outside the workspace to avoid
recursive copying. Keep input installations quiescent during capture/staging.
Each regular file is hashed; directory/file modes and symbolic-link text are
recorded. Inputs are compared before copying and copied bytes are checked again.
The bundled Bell example deliberately replaces any older fixture copy and the
final payload inventory records the resulting bytes.

Symbolic links resolve against the declared container layout, never the host's
`/work` paths. Absolute XACC plugin links to declared installed Core libraries are
preserved. Missing targets, cycles, special files and directory symlinks are
rejected. Generated container directories are traversable by UID65532 even under
a private host umask; inaccessible captured files/directories fail staging.
A failed context has no completion record and must not be built.

`inputs.json` says `observed_installed_bytes_not_verified_build_origin`.
Current source HEADs cannot prove how reused binaries were built. Retain the
input receipt and context record hash outside the staging directory: verification
checks consistency, not authenticity, and cannot detect an attacker replacing
both files and all their hashes. These files are not platform admission receipts.

## Next native step

After the context passes verification, on the authorized isolated Linux amd64
build host:

```sh
docker buildx build --platform linux/amd64 --load \
  --iidfile /tmp/cpu-image-id --tag qristal-cpu:local /tmp/cpu-context
python3 -B qualification/runtime/test_image.py --image "$(cat /tmp/cpu-image-id)"
```

This is a proposed execution recipe, not a recorded success. Use the existing
bounded build host and its resource/time supervision; the Dockerfile itself is
not a resource controller. The runtime test harness applies the existing container
limits and runs without host mounts. Record its ten groups, including all43
functional fixtures, against the exact newly assembled identity. Preserve failure
logs and the context hash. Do not update the artifact catalog until this passes.

The base is digest-pinned Ubuntu22.04 and top-level apt versions use the existing
list. Live apt repositories must still retain those versions; full resolution is
recorded inside the image and is not snapshot-pinned. No byte-identical rebuild
claim is made. No late readout/program/preparation helper is silently added to the
baked payload. Adding those requires its own scope and native qualification.

The next provenance increment must bind installed bytes to actual build receipts
from controlled source acquisition/compilation. Then add registry publication,
SBOM/attestations and acquisition verification. This batch supplies staging and
checks, not those remaining release gates.

## Isolated native runner

The [predeclared native plan](NATIVE-PLAN.md) uses the existing fixed CPU VM
supervisor rather than shared Docker. From the independent checkout:

```sh
python3 -B qualification/cpu_package/pack_native.py /tmp/cpu-context /tmp/cpu-native-artifact
python3 -B qualification/cpu_package/run_native.py /tmp/cpu-native-artifact /tmp/cpu-native-run
```

Packing creates an archive of the checked context and exactly three named harness
files. Running uses the existing AWS session and creates the plan's single VM,
private transfer bucket and dedicated security group. The runner enforces the
original deadline and verifies exact cleanup. These commands execute an experiment;
they do not publish an image. Never run the cloud step as an offline CI test.

A recovered report can contain a bootstrap, build or test failure. After recovery,
use `check_native.py REPORT MANIFEST` to distinguish a pass from failure; the
manifest is the packer's `manifest.json`. Independently retain and verify the
supervisor's cleanup records. Script hashes bind the precise harness, while the
context record binds the staged bytes. Future harness changes require new evidence
or verification against the historical source revision.

## Recorded native result

The [13 September native experiment](../evidence/2026-09-13-cpu-oci/README.md)
built this context in102.90seconds and passed the ten existing test groups in
4.48seconds. Exact VM/disk/group/transfer cleanup passed. The image was disposable
and was not exported or published. The inherited GPU-negative invocation rejected
a missing program before reaching backend selection; that specific rejection
remains unverified. Read the evidence limits before using this as a release claim.
