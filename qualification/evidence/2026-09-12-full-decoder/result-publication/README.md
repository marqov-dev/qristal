# Caller-result repair: standalone and syntax evidence

Decoder 4d330ba adds a production result accumulator and caller-visible metadata.
53 standalone C++ checks passed with Release flags, AddressSanitizer and
UndefinedBehaviorSanitizer on macOS arm64. Ten new checks cover threshold/sample
mismatch, maximum-pair preservation, strict improvements, invalid strings,
negative scores, no-improvement behavior and trial accounting. The other 43
register/score checks continue to pass. No simulator was executed.

Full source and expanded XACC-test syntax checking passed with the documented
libc++ compatibility switch, suppressing only deprecation warnings. This does
not validate runtime service lookup, linked execution or installed packaging.
The earlier three native tests still apply only to the table-only revision.
Native execution and output semantics must be requalified when the release lane
no longer needs shared Docker. No Docker or AWS resources were launched here.
