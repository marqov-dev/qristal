# Portable source-built QPP input context

Prepared from the successful Core native archive after PR45 merged as
`0e85909813cf5794092e21c0a9acaa5f3ad2c5cb`. This was a local file-staging
operation: no install, image build, simulator execution or AWS resource was used.

The real artifact passed the unchanged native/archive validators and the packaging
input gate again. All 50 acquired Python wheels matched the executed material
manifest; the retained ANTLR wheel brings the staged total to 51. The installation
payload preserves 5,432 original entries and exact file hashes/modes/relative
links. A separate serialized-tar readback matched the original selected inventory.

Initial directory extraction failed safely on this Mac because XACC contains both
`Json.hpp` and `json.hpp`. The corrected portable path retains `work.tar`, with
roots `install-core` and `install-xacc`, for future case-sensitive Linux extraction
into `/work`. Neither filename is renamed or omitted. No failed output was promoted.

The complete staged context was independently copied and hash-verified into
`/Users/david/Marqov Artifacts/qristal/qpp-context-2026-09-14`, outside temporary
storage; the working copy is `/private/tmp/qpp-runtime-context-20260914`.
Compiled libraries and wheels are not committed. `result.json` binds the full
staging manifest and payload identity; `runtime-recipe.json` records asset hashes,
layout and restrictions. Original alternate-recovery provenance remains explicit.

The QPP-only entry point rejects other backend/noise requests before native code.
This is a local CLI contract; it does not restrict arbitrary Python code or provide
the hosted security boundary. No claims of native final-image replay are made.
The recipe remains build_ready=false pending exact OS package closure and notices;
see `qualification/core_package/OS-PLAN.md` for concrete next steps.
