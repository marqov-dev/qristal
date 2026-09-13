# Core exported-source preparation

Locked source: `a5c3e5fa544c07d538974d3a289b19652d483848`.

The verified source export was prepared without configuring, compiling, installing,
or contacting AWS. Both the Eigen staging and explicit-version transformations
were checked against complete original-file hashes and retained patch bytes.
The derived tree passed the effective-manifest verifier; its manifest SHA256 is
recorded in `preparation.json`. The pristine inputs were not edited.

The source-cache command `git describe --tags --abbrev=0` at this locked revision
returned `v1.8.1`, whose commit is
`a0bcfbf4e56adf443e981469e90013e999015183`. The locked revision is a later commit;
this label preserves CMake's previous selection, not a claim of release identity
or signed publisher provenance.

Nine offline unit tests passed, including rejection of changed version-source
bytes and a changed version patch. This is source-preparation evidence only:
Core native configure/build, retained fresh XACC installation, complete native
Python environment and published runtime qualification remain outstanding.
