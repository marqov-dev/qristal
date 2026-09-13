# Core output retention boundary

This module does not run workloads, install software, launch cloud resources or
publish images. It keeps the previous XACC artifact verifier unchanged.

Use `normalize(base)` only on the disposable sibling `install-core` and
`install-xacc` prefixes, **before** installed-only consumers are compiled/run.
The helper accepts only Core's nine named plugin links whose absolute targets
are `/work/install-core/lib/lib<known-plugin>.so[.version]`. The existing local
target must be a file contained within the derived Core lib directory. It
replaces each link atomically with `../../install-core/lib/<filename>` and
returns a change receipt with target hashes. Unknown absolute plugin links fail
before any changes. Filesystem errors during replacement can leave a partial
derivative; preserve failure evidence and discard that derivative. This is an
explicit install-layout transformation, not an upstream build claim.

The guest must attach the returned receipt as `plugin_normalization` to its
report. The report alone does not prove ordering: its independent native checker
must require normalization before installed-only consumer replay and require
successful replay after the final transformation. A consumer tested before
normalization is insufficient.

`pack(output, report, roots)` and `verify(archive, identity, report)` use an
independent bounded tar format (1 GiB compressed/expanded, 50,000 members).
The receipt includes every directory mode, regular file mode/size/hash and
relative symlink target. Verification reads tar members without extracting or
executing them; it rejects absolute/escaping/dangling/cyclic links, special files,
hardlinks, duplicate members and non-directory ancestors. Original report bytes,
receipt and archive are independently hash-bound. Successful archive verification
is not native qualification; the parent must classify the native report first.
For successful output, `report.retained_files` must map every regular file under
`antlr/`, `consumer/` and `consumer-output/` to its SHA256, including at least one
source and one built consumer. Capture these identities from the actual replay
inputs/outputs; the verifier rejects a packaged consumer that differs from them.

Successful reports accept exactly these explicitly staged output roots:

- `install-core` and `install-xacc`: sibling derived installs.
- `antlr`: only `antlr4_python3_runtime-4.9.2-py3-none-any.whl`.
- `consumer` and `consumer-output`: isolated fixture source and built consumer,
  never a source repository, user home, environment directory or entire `/proof`.
- `logs`: only `<stage>.log` for recorded `report.stages`, matching each stage's
  `log_sha256`. Stage names are restricted to lowercase letters, digits/hyphens.

Failed reports accept only `logs`; report and receipt are added automatically.
Thus a failed build can retain complete named stage logs and its original report
without labelling partial installs usable. Empty stages may retain an empty logs
directory and a bootstrap failure report. Never stage cloud-init user data,
curl configurations, signed URLs, credentials or environment dumps in these
roots or logs. The file boundary prevents arbitrary `/proof` capture; it does
not inspect log text for secrets. The guest must suppress request secrets at
their source as the existing wrappers do.

CLI examples (all paths supplied explicitly):

```
python3 output.py normalize /work /proof/plugin-normalization.json
python3 output.py pack /proof/report.json /proof/output-roots.json /proof/output.tar.gz /proof/output-identity.json
python3 output.py verify output.tar.gz output-identity.json report.json
```

The parent owns upload/download deadlines, private transport, durability (`fsync`
before deleting remote evidence), failure recovery state and verified cleanup.
No cloud behavior or native build has been exercised by these offline tests.
