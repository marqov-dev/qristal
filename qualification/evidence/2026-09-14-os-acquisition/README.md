# Offline-built QPP image: local emulation proof

PR46 merged at `2d80af863eba6a57e0c19c27bd1b28da710c2cc8`. This batch acquired
and authenticated runtime OS inputs, assembled the existing source-built QPP
payload, built an image offline and ran six isolated local CLI probes. The Docker
host reports linux/aarch64; all image work requested linux/amd64. **This is
emulation evidence, not native amd64 hardware or hosted execution qualification.**

## Results

- 36 Debian package files (24.3 MB downloaded) match three Ubuntu-signed releases
  and six authenticated Packages indexes at the configured 20260913T000000Z
  snapshot. The explicit Ubuntu keyring hash and package identities are in
  `os-lock.json`. Base and post-acquisition dpkg status are identical. Packages
  inherited from the exact base remain part of the closure; the verifier does
  not independently prove resolver completeness or image origin.
- The final BuildKit image build ran with `--network none`. Local APT installation
  and its dependency check passed. Python installed the 50 locked wheels plus
  retained ANTLR; `PIP_FORCE_REINSTALL=1` prevents same-version bootstrap
  setuptools from bypassing replacement. `pip check` passed.
- Image ID: `sha256:8d8a81d995325ae9c452dca2698442b02c735cc6eae9d98ea78a38532a5a8266`.
  The final build log also retains config, platform manifest and index identities.
- Six local probes passed: QPP-only capability declaration, identity (`00:256`),
  Bell (both `00` and `11`, 256 total), asymmetric q0 flip (`10:256`), Aer rejection
  and nonzero-noise rejection. Counts, bit ordering and program hashes were checked.
  Containers used nonroot uid65532, network none, read-only filesystem, two CPUs,
  4GiB memory, 256 PIDs, dropped capabilities and no-new-privileges. Exact container
  absence was verified after every case. See `local-probe.json`.
- 454 offline tests passed across 27 suites. Review covered staging identity,
  archive signatures, local dependency installation and cleanup classification.

## Findings and corrected failures

The minimal base had no CA bundle. The first acquisition failed certificate
validation; the successful retry mounted the host's public CA bundle read-only.
No TLS or archive-signature checks were disabled. APT sources are acquisition
configuration, not outbound firewall enforcement.

The deprecated legacy Docker builder failed exporting cached base content, even
after reacquiring the same digest. BuildKit succeeded. APT's `--no-download` local
file mode failed with an internal relative-path error; directly installing every
.deb with dpkg then exposed Python pre-dependency order. Normal APT local-file
installation under the network-disabled build handles the ordering correctly.

The initial smoke probe produced correct application results but stayed red because
its cleanup checker rejected Docker's blank stdout line. The corrected checker
accepts the explicit absent-container error and distinguishes daemon failures;
the final rerun records successful application results and cleanup. Earlier failure
logs/receipt are preserved, not overwritten or relabeled as successes.

## Notice inventory and retention

The wheel scan observed 86 notice files across 51 wheels and 17 named native notice
files. Filename-matched/declared notices were not observed for ANTLR, openpulse or
ply; matplotlib's declared paths need reconciliation with its bundled layout.
These observations are incomplete coverage, not conclusions about license grants.

All 36 selected OS packages resolve to copyright files, eight via archive-contained
links. Parsed common-license references also resolve. `os-notice-observations.json`
retains exact source hashes, member paths and link chains; the executed read-only
scanner is included. Complete native source/dependency and inherited OS coverage,
source obligations and final attribution remain to be reviewed before distribution.

Authenticated OS bytes, signed metadata and acquisition records are retained at
`/Users/david/Marqov Artifacts/qristal/os-inputs-2026-09-14`. The image is saved
privately at `/Users/david/Marqov Artifacts/qristal/qpp-local-image-2026-09-14.tar`;
its archive hash is recorded separately after export. No packages or compiled image
are committed to Git or published. The prior native artifact's alternate recovery
provenance remains unchanged; packaging does not recreate its missing console hash.

Next: complete notice coverage and an image-wide ELF/plugin inventory, replay from
the saved distribution artifact, then native amd64 qualification and exact hosted
image/profile admission coordinated with the managed-execution owner. No AWS
resources were created and no main platform checkout was changed in this batch.
