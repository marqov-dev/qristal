# CPU OCI build and native qualification — 13 September 2026

**The explicit CPU image recipe built and passed the existing ten native test
groups on an independent AWS CPU VM.** Build102.90seconds; tests4.48seconds.
The built, inspected and tested configuration ID was
`sha256:cba7a42f57222dab82d040073e085213d1737d405cad14abaaf58de53dd39b6e`.

Execution harness commit: `47753cd`, based on merged PR34
`f640543825475d3d94c508290135d8bbba095cc3`. Native manifest hashes bind the actual
three harness files and the previously recorded CPU context. Docker29.1.3 on the
fixed Ubuntu22.04 m7i.large host assembled the digest-pinned Ubuntu image from
captured installed libraries; this did not freshly compile those libraries.

The matrix includes43 functional fixtures (8Core,10noise,16Integrations,
9simplifiedDecoder), capabilities, ideal/noisy Bell sampling, two rejection
invocations and non-root/no-build-tree/no-compiler checks. Containers used the
recorded CPU/memory/PID restrictions, read-only root, dropped capabilities,
no networking and no host mounts. No source overlay was used.

## A negative-test limitation discovered

The inherited `reject-gpu` invocation has no `--qasm` input. Its actual diagnostic
was `qristal_sample_failed:program_file`, not unsupported-backend rejection. Its
exit2 is real, but it establishes only missing-program rejection. Do not count
this result as proof of GPU-backend rejection. The next revised matrix should
supply a valid Bell program and assert the backend-specific diagnostic.
No post-result retry or silent reinterpretation was performed.

## Evidence and cleanup

`result.json` retains the complete test command/exit observations and bounded
build/check/log tails with full-log hashes. Some fixture PASS lines precede the
retained tails; the source-bound test harness checked them in the guest. Full
logs and the newly built image were not exported and disappeared with the VM.
This is evidence of a successful disposable build, not a downloadable release.
The full resolved apt inventory exists in the recipe's image but was not exported
by this protocol; build tails alone are not a complete SBOM or package inventory.

Console records recover the exact report by checksum. AWS identifiers in retained
lifecycle records are consistently pseudonymized. Original exact records remain
private. Cleanup verified termination, disappearance of the exact root volume,
deletion/absence of the dedicated security group, and deletion/absence of the
private transfer bucket. No hosted service or persistent infrastructure remains.

```sh
python3 -B qualification/cpu_package/check_evidence.py qualification/evidence/2026-09-13-cpu-oci
```

The verifier checks retained bytes, console recovery, harness/context/image
bindings, exact permitted test commands and cleanup identity relationships. It
reports GPU-backend rejection unverified. This is consistency checking of saved
operator observations, not publisher authenticity or production attestation.

Next: correct the negative fixture in a new matrix, export package inventory and
notices/SBOM, publish an immutable CPU candidate, and qualify its acquired registry
identity. The old catalog remains unchanged. Original installed build provenance,
byte-identical reproducibility, public redistribution and hosted admission remain
separate gates. Standalone GPU evidence is unchanged; full Decoder remains outside
this CPU result.
