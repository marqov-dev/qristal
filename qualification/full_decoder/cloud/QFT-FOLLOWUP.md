# Public QFT dependency diagnostic — separately declared third experiment

The bundle-corrected VM loaded the rebuilt Core library, with matching file/path
identity, and passed all six initialization tests. The tiny program entered
Decoder circuit construction, reported missing `iqft`, and exited 139. Cleanup
completed automatically with exact instance/disk/group and transfer absence.
No candidate or successful caller-result observation was produced.

Source trace at XACC d1edaa7ae53edc7e335f46d33160f93d6020aaa3:
`quantum/plugins/circuits/qft/InverseQFT.cpp` implements iqft using qft;
`QFT.cpp` implements qft. `GeneratorsActivator.cpp` registers both in the
`xacc-circuits` bundle. The installed qualification prefix has no
`libxacc-circuits.so`. Core phase_estimation.cpp requests iqft and dereferences
the resulting instruction. The missing service is a public dependency omitted
from our selected installed build, not missing proprietary QB IP.

One new VM will compile those two unchanged upstream implementations into an
explicitly named qualification-only provider with a minimal activator. This is
a dependency diagnostic, not restoration or qualification of the complete XACC
generators bundle. The pack manifest adds the exact XACC revision and QFT source
hashes. The tiny fixture now checks qft/iqft availability before construction.

Keep the same 2-vCPU/8-GiB VM, 4-GiB child address-space limit, 180-second compile
limits, 60-second fixture limit and 20-minute supervisor/five-minute cleanup.
Provider resource generation and append each have a 30-second bound. Disable
guest core dumps. No algorithm changes, source-lock promotion, automatic retries
or deadline extensions. Retain failure and stop native experimentation after
this diagnostic; use its evidence to choose the next bounded source task.
