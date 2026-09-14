# Final QPP runtime OS gate

Read-only inspection of the successful source-built artifact in
`qualification/evidence/2026-09-13-core-native-success` found no unresolved
libraries in its installed-linkage log. That log resolved 37 OS-provided SONAMEs.
It is evidence about the native builder, not the final runtime dependency closure:
the scan does not cover every Python wheel extension or every XACC plugin.

The old `qualification/runtime/apt-runtime.txt` is therefore a reference, not
an install-ready lock. It lacks the venv package required by the new offline
Python reconstruction. The observed interpreter/shared-library patch version is
3.10.12-1~22.04.18; acquire matching `python3.10`, `python3.10-venv` and
`libpython3.10`, including dependencies. Native libc6 was 2.35-0ubuntu3.15;
do not assume the pinned Ubuntu base already contains that version.

Observed OS library families map to libc6, libstdc++6, libgcc-s1, libgomp1,
libpython3.10, libcurl4, libssl3, libbrotli1, libexpat1, libffi8, libgmp10,
libgnutls30, libhogweed6, libnettle8, libgssapi-krb5-2, libkrb5-3,
libk5crypto3, libkrb5support0, libkeyutils1, libcom-err2, libldap-2.5-0,
libsasl2-2, libnghttp2-14, libidn2-0, libpsl5, librtmp1, libssh-4,
libp11-kit0, libtasn1-6, libunistring2, zlib1g and libzstd1. These are
library-to-package mappings, not a claim that this list is a complete apt closure.
Keep OpenBLAS/gfortran/quadmath requirements conservative until wheel/plugin
scanning and native final-image tests show whether they can be removed.

Next bounded acquisition/build experiment:

1. Resolve a minimal Ubuntu 22.04 linux/amd64 runtime package closure including
   Python venv, against signed repository metadata. Save exact .deb bytes, hashes,
   metadata and package copyright notices. Retain repository/snapshot identities;
   do not silently substitute unavailable historical versions.
2. Build with the pinned base and offline package/wheel inputs. Recreate Python at
   `/work/python-core`; preserve the exact sibling Core/XACC installation prefixes.
   Record final dpkg inventory and pip check/freeze. Keep compiler and source trees
   out of the runtime.
3. Scan all shipped ELF files, Python wheel extensions and plugins for unresolved
   libraries. Run installed-only identity/Bell and local CLI schema/count/bit-order
   checks with nonroot, read-only, networkless CPU/memory/PID limits. Ensure Aer and
   noise fail at the CLI boundary.
4. Collect complete notices from exact source inputs and OS/Python distributions,
   bind an immutable candidate identity, then repeat via the acquired image digest.
   Hosted profile admission remains a separate owner-coordinated gate.

No new VM or image build was performed for this staging batch. Historical native
build success and the artifact's alternate recovery provenance are preserved;
neither establishes reproducibility or final-image qualification.
