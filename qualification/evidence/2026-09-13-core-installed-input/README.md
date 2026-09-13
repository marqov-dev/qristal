# Core installed dependency input

The complete retained XACC archive passed verification again and was copied into
an archive-only transport bundle without extraction or binary execution. Original
archive identity, required Linux mount prefix and staging-manifest hash are in
`transport.json`. Seven offline helper tests passed.

A local tree-materialization attempt encountered case-distinct XACC headers on
the case-insensitive host and failed before promoting output. The transport
preserves both filenames; Linux extraction and native consumer replay are not
claimed by this evidence. See `qualification/installed_inputs/README.md`.
