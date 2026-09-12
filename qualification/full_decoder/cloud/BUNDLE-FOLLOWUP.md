# Bundle packaging correction — second, separately declared experiment

The first CPU VM rebuilt Core and both executables; all six initialization tests
passed. The tiny program exited 255 before simulation. XACC reported that the
new Core search library had no readable bundle zip, then sparse-sim was absent
from the failed plugin registry. This is a new harness omission, not evidence
that sparse-sim or Decoder failed to simulate the fixture.

The retained original generated build rule resolves the omission:
`build-core/CMakeFiles/algorithm_es.dir/build.make:161` runs
`usResourceCompiler4 -b libalgorithm_es.so.1.8.1 -z algorithm_es/res_0.zip` after
linking. The generated resources C++ file contains only a linker placeholder.

One new experiment adds that exact public resource compiler and post-link step.
It keeps the original VM size, 20-minute supervision, five-minute cleanup,
180-second builds, six initialization cases and 60-second tiny fixture. Bundle
append has a 30-second bound. No algorithm/source-lock change, enlarged fixture
budget or automatic retry is authorized by this protocol.

The Linux tiny consumer additionally enumerates loaded objects after XACC
initialization. Exactly one Core search library must be present. Its observed
allowlisted path is hashed in the guest and compared with the just-built bundle.
This distinguishes merely copying a binary from observing its mapped path.
The workload cannot modify installed libraries, but this is still not an
independent attestation or installed Decoder-plugin qualification.

Keep the first failure and its cleanup recovery alongside this follow-up. The
initial supervisor cleanup stopped on instance_ownership during termination;
resuming unchanged code after the same bound instance became terminated verified
its exact disk and dedicated group absent within the original deadline. Transfer
cleanup succeeded on the initial attempt. Do not call that unattended success.
