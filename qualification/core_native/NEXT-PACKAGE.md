# Source-built runtime follow-up

This plan is conditional on successful native Core classification and verified
retention. It does not describe work already completed or admit a hosted runtime.

1. Retain the complete successful Core archive, independent classification and
   cleanup receipt. The native probe covers identity and Bell through Core QPP's
   C++ and Python APIs: two fixtures, four executions. It does not requalify Aer
   or the historical 43-fixture matrix.
2. Add a separate source-built packaging context preparer. The historical
   `cpu_package/stage.py` expects Integrations/Decoder installation trees and
   rejects the normalized sibling links now retained in Core's XACC installation.
   Validate those links against the new exact receipt; preserve the older
   validator and its evidence contract.
3. Recreate Python offline from the locked fifty-wheel input plus the retained
   ANTLR wheel, then run `pip check`. The successful Core output intentionally
   excludes its build virtualenv. Preserve Python 3.10 and native ABI compatibility
   and collect component notices from verified source materials.
4. Build and test a QPP-scoped runtime first. Do not reuse the Aer capability
   declaration or the broader Integrations/Decoder matrix without native evidence
   for the changed image. Require non-root, read-only, network-disabled execution,
   explicit backend rejection and acquired-image checks.
5. Publish a distinct immutable candidate with source/build/install provenance
   bound to the new receipts. Historical `cpu_release/prepare.py` and inventory
   records intentionally mark original binary provenance unverified; do not
   rewrite their history to describe the new candidate.

The current Docker recipe resolves OS packages from live apt repositories.
Repeatable source acquisition is distinct from byte-identical rebuilds; the
latter also requires retained or snapshot-pinned OS packages and a comparison
build. Neither claim is established by one successful native run.

Packaging remains independent of hosted execution admission. Main-agent
infrastructure, runtime authority and hosted result/lifecycle receipts are
separate gates. Full Decoder remains lower priority.
