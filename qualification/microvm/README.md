# Disposable-host CPU microVM qualification

This is the retained synthetic experiment, not a hosted executor or production
security boundary. The three guest/supervisor scripts are byte-for-byte the scripts
from the successful run. They are intentionally specific to a disposable host and
fixed two-qubit fixture; they are not safe general-purpose launch services.

Read [the evidence and limits](../evidence/2026-09-11-microvm/README.md) first.
The offline checker needs only Python's standard library and launches nothing:

```sh
python3 qualification/microvm/check_evidence.py qualification/evidence/2026-09-11-microvm/passed
python3 -m unittest discover -s qualification/microvm -p 'test_*.py' -v
```

The checker detects internally inconsistent evidence; anyone able to replace the
report and logs can fabricate a consistent transcript. It is not attestation,
semantic proof, admission, or a result-acceptance writer.

## Inputs and environment

A separately authorised, disposable Linux x86-64 host with usable `/dev/kvm`,
cgroup v2 CPU/memory/pids controllers, root access, Python 3, `tar`, `truncate`,
`mount`, `install`, and `mkfs.ext4` is required. No host is provisioned by this package.
The operator must arrange an independent host shutdown/termination deadline and
cleanup before running privileged commands. Do not run on a developer workstation,
shared host or production machine. Scripts write `/qb-host-canary`,
`/run/qb-management.sock`, `/srv/jailer/firecracker` and `/opt/qb-proof`.

Use the qualified joined-pipeline image described in
[the runtime recipe](../runtime/README.md). The tested local image was
`sha256:89bcfeac18c20792799f9fa91e1876e57ef4e3f9c7339757bf8e520686fe0c44`.
It was not published to a registry. Rebuilding from public sources can produce a
different image/export hash; record and qualify that new artifact rather than
claiming it is the retained image. An export of the earlier base image without
`program_guard` and `local_pipeline` is insufficient.

On the build machine, export the selected existing image without starting it:

```sh
container=$(docker create IMAGE_ID)
docker export --output rootfs.tar "$container"
docker rm "$container"
```

Acquire these public inputs on a networked preparation machine:

- [Firecracker 1.16.1 x86-64 release](https://github.com/firecracker-microvm/firecracker/releases/download/v1.16.1/firecracker-v1.16.1-x86_64.tgz).
- [Guest kernel 6.1.155](https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.15/x86_64/vmlinux-6.1.155).

The [artifact hashes](../evidence/2026-09-11-microvm/artifact-hashes.json) identify
the observed export, binaries and scripts. The Firecracker release digest was
checked against its published asset digest; the kernel hash was recorded after
download and is not a separately verified signature. Keep the manifest outside
the guest. Transfer the assets plus the three scripts to `/opt/qb-proof` on the
approved host. Transfer credentials belong to the operator/host, never the guest.

## Assemble and run on that host

Verify the input hashes first. For the retained exact artifacts, put their manifest
in `/opt/qb-proof/artifact-hashes.json` and run:

```sh
cd /opt/qb-proof
python3 - <<'PY'
import hashlib, json
from pathlib import Path
hashes = json.loads(Path('artifact-hashes.json').read_text())
for name, expected in hashes.items():
    digest = hashlib.sha256()
    with open(name, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise SystemExit('Hash mismatch: ' + name)
print('Input hashes match')
PY
```

For an independently rebuilt runtime, retain a separate manifest and identify it
as a new qualification run. Do not overwrite historical evidence or its hashes.
Use a fresh host workspace for each reproduction; allow at least 15 GiB free disk.
The root disk copies are not covered by the guest RAM cap.

```sh
cd /opt/qb-proof
mkdir release rootdir
tar -xzf firecracker-v1.16.1-x86_64.tgz -C release
install -m755 release/release-v1.16.1-x86_64/firecracker-v1.16.1-x86_64 /usr/local/bin/firecracker
install -m755 release/release-v1.16.1-x86_64/jailer-v1.16.1-x86_64 /usr/local/bin/jailer
tar -xf rootfs.tar -C rootdir
install -m755 guest_init.py rootdir/qb-init.py
install -m644 guest_workload.py rootdir/guest_workload.py
mkdir -p rootdir/inputs rootdir/dev rootdir/proc rootdir/sys rootdir/tmp
truncate -s 1536M rootfs.ext4
mkfs.ext4 -q -F -d rootdir rootfs.ext4
python3 host_test.py
```

Only unpack a trusted, selected runtime export with these privileged commands.
The ext4 conversion adds bootstrap files, so the VM filesystem is a derivative of
the OCI export, not the original OCI image. Filesystem timestamps/UUIDs and upstream
package acquisition mean byte-identical rebuilds are not claimed.

One guest runs at a time, with two vCPUs, 4 GiB guest memory and a 90-second guest
execution deadline. Jailer requests two host CPUs, 5 GiB memory and 256 PIDs. The
whole command also copies disks between guests; the operator's external host
lifetime bound must cover those stages and failures outside the VMM loop.

Retain `report.json` and each referenced `*.console`, plus the artifact manifest,
configuration files and effective host configuration. Run the offline checker on
that output directory. Afterwards verify the exact VMM processes are gone and
remove the disposable host/storage using the operator's approved cleanup path.
A killed orchestrator or disk-copy failure is not automatically reconciled by these
scripts. A production service needs durable ownership, recovery and resource accounting.

Do not import `host_test.py`: it is an executable experiment with top-level host
side effects. `guest_init.py` is guest PID 1 and must never be run on the host.
