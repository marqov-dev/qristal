# Native operator restart and exact cleanup

Recorded on 11 September 2026 in America/Toronto (12 September UTC).
This is an AWS supervisor lifecycle experiment, **not another simulator run**.

One g5.xlarge in us-east-1c booted the previously inspected Ubuntu GPU AMI,
ran an installed NVIDIA health query, waited 90 seconds and emitted a bounded,
checksummed result. It reported NVIDIA A10G, driver 595.91.07 and 23,028 MiB,
with return code zero. No container transfer, dependency installation,
simulator execution, commercial QB component or workload credential was needed.
The group was configured without inbound or outbound rules; no instance role or
SSH key was supplied. A guest-side eight-minute shutdown was scheduled.

The local supervisor was SIGKILLed after it flushed instance
i-0e6877c4d317c34b9 and root volume vol-089bdde40f6f2b071. Its exit status was
-9. A new resume process recovered the same guest's result. The resume action
has no launch call. Both absolute deadlines stayed unchanged: ten minutes for
observation and five additional minutes for cleanup, fixed before launch.

## Failures retained, not hidden

1. The preparation adapter's /dev/stdin JSON input failed AWS CLI parameter
   validation before resource creation. A filtered group-name lookup found zero
   matching groups. Source 80e6772 replaced stdin with a private 0600 temporary
   request file, removed after the call; a regression test verifies that behavior.
2. AWS omitted SubnetId after instance termination. The initial cleanup
   ownership check rejected that response. No cleanup success was written.
   terminal-metadata-failure.json retains the safe identity fields and failure.
3. Correction 8fceb1f permits absent subnet only for the already-bound exact ID
   in terminated state, while still requiring the original client token.
   Explicit cleanup then completed on the same resources, within the original
   deadline. Both actual supervisor source versions are retained under operator/.

Therefore this records successful result recovery after an abrupt observer kill
and exact cleanup **after a code correction**. It is not evidence that the original
supervisor completed unattended on its first attempt. A future release soak can
repeat interruption using the corrected version end to end.

## Cleanup evidence

cleanup.json records observed termination, exact-volume absence and group
absence. A separate read-only verification checked the original client token:
exactly one matching instance, terminated; zero matching exact volumes; zero
matching groups for sg-0b710515b7e147346. verification.json retains those
observations. No S3 bucket or transfer object was created in this experiment.
This closes the earlier volume-identity evidence gap for **this** run; it does
not rewrite or strengthen the historical published-image cleanup record.

The journal, interruption receipt, filtered chunks and decoded health
result are retained. Raw bootstrap/EC2 console logs are excluded. The guest
bootstrap here contains no signed URLs or secrets. Operator snapshots are
historical reproduction evidence, not instructions to rerun fixed resource IDs.

## Offline verification

Run python3 qualification/gpu_release/check_supervisor.py with this directory as
its argument, then the gpu_release unittest suite.

The checker reassembles the checksummed native health payload, binds original
and final resource IDs/deadlines, and verifies both cleanup records. Five tests
cover replay and semantic mutations of deadlines, disk identity, completion and
payload. The manifest detects changes to retained bytes; it is not a provider
signature or platform-accepted receipt. Hosted admission, authenticated transport,
tenant reuse, long-kernel interruption and GPU memory sanitization remain outside
this proof.
