# Native image preparation — not execution evidence

PR49 merge: `25559c95220e3e49e3ec1c75346658cd95bc3591`.
The exact image and all native/cloud operator inputs are frozen. Preparation
reverified the saved image archive, checked the cloud protocol inside the transfer
archive, and compared every frozen input/operator hash. No VM was launched.

The checked-in protocols and preparation receipt describe the next bounded run.
The binary transfer archive remains private. Read-only AWS preflight confirmed
the expected account and available amd64 AMI; it does not grant or prove launch
permissions, capacity, hosted admission or completed native tests.

Offline replay passed 501 tests across 27 suites. New tests cover native host and
image identity rejection, raw receipt preservation, all nine case requirements,
protocol mismatch before resource activity, and verified-retention-before-deletion.
Failure-path tests ensure unverified recovery objects are retained.

See `../../core_package/NATIVE-IMAGE-RUN.md` for the exact command, hashes, resource
limits and remaining authorization. Native execution, cloud cleanup and hosted
results must be recorded in separate subsequent evidence, never added as success
flags to these preparation receipts.
