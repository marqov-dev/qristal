# Core input upload timeout

The first approved Core attempt timed out during its bounded 600-second input
upload. It never attempted a security group or VM launch. This is a transfer
failure, not a Core configure/build failure.

The runner conservatively preserved the bucket. A subsequent exact-scope check
verified its ownership tag, empty contents and absence of tagged instances, then
deleted the empty bucket and verified absence. No compute was created. Raw
identities remain local; retained lifecycle metadata uses consistent aliases.

The unchanged approved package can be retried within the still-unused single-VM
scope. This record does not claim a successful upload or native qualification.

The second single-request upload also reached its 600-second timeout before
security group or VM launch. Its separate empty bucket was likewise verified
and deleted. The two attempts consumed no VM launch; the approved archive
identity was unchanged. Multipart transport is a proposed operator-only fix,
not evidence that native Core works.

A third prelaunch attempt used two 8 MiB multipart workers. It uploaded 15 of
38 parts before the same 600-second limit. Exact-upload abort and multipart
absence were verified; the empty owned bucket was then deleted and absence
verified. No VM launched. This established transfer progress and successful
failure cleanup, but not a completed archive upload. The executed wrapper is
retained under `multipart-operator/` to preserve its recorded source hash.
A subsequent operator-only revision allows 3600 seconds for upload, separately
from the unchanged 3600-second VM observation and 300-second cleanup windows.
