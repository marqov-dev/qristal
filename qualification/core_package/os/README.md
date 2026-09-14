# QPP offline OS inputs and local image experiment

Use Ubuntu's existing APT resolver and signed snapshot metadata; do not implement
a dependency solver in the packaging code. The fixed snapshot is
20260913T000000Z, with jammy/jammy-updates/jammy-security main and universe.
See https://snapshot.ubuntu.com/ for the service contract and snapshot semantics.

`collect.sh` runs only in the disposable pinned amd64 Ubuntu base. It downloads
requested packages and dependencies without installing them and compares the
before/after dpkg status. The minimal base lacks CA certificates; supply a public
CA trust bundle read-only at `/trust.pem`. Both HTTPS certificate validation and
Ubuntu archive signature checks stay enabled. Retain the collector source/hash,
public bundle identity, resolver log, base status, archive keyring, signed release
files, compressed indexes, downloaded packages and base documentation.

`os_lock.py INPUTS NEW_LOCK.json` independently verifies all three InRelease
signatures with the explicitly pinned Ubuntu archive keyring in a fresh gpgv
home. All six decompressed indexes must match signed hashes/sizes, and every
.deb must match an authenticated package record. The package set is relative to
the pinned base and its recorded inherited packages; it is not a standalone
closure. Snapshot configuration comes from the acquisition record, not a distinct
cryptographic snapshot attestation. Installation/ABI compatibility is a later test.

`assemble.py STAGED OS_INPUTS NEW_CONTEXT --expected-staging-sha256 HASH` requires
the retained staging receipt hash, checks OS signatures and snapshots all selected
inputs before publishing a new context. Use BuildKit with `--platform linux/amd64
--network none` for its Dockerfile. All OS package paths and Python wheels are
local. APT's normal local-file mode preserves pre-dependency ordering; its
`--no-download` option caused an internal relative-path error in this base. The
build's network namespace supplies offline enforcement. Direct unordered dpkg
installation is also unsuitable for Python's pre-dependencies.

A successful image build is not native hardware qualification, hosted admission
or redistribution clearance. The observed local Docker host is ARM; amd64
containers run via emulation. Record the final image identity, dpkg and pip
inventories and bounded QPP results separately. Full source/dependency notice
coverage, final image-wide ELF/plugin scans, acquired-digest replay and native
hosted admission remain distinct gates. Do not publish acquired packages or the
compiled image merely because preparation and installation pass.
