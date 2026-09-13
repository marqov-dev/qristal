# Offline conference packet

Export the existing saved research as one self-contained HTML page and an
allowlisted ZIP of supporting records. No simulator, Docker, service, cloud
resource or dependency installation is started.

Run python3 qualification/conference/packet/export.py --output NEW_DIRECTORY.
Open index.html in a browser. Figures are embedded; no network is needed to show
them. External source links and the Marqov report still need network access.
The ZIP retains the HTML, source revision, SHA256 manifest and25 explicitly
selected evidence files, including the current conference summary. It is a research subset, not a complete standalone
reproduction bundle; use repository qualification tools for full evidence checks.

No directory crawling occurs: only public research files named in FILES are
included. Source symlinks/path escape and oversized inputs are rejected.
The output directory must be new. ZIP entries and hashes are checked after export.
Synthetic coverage and native simulator observations have separate labels.

This provides a conference backup if app connectivity is unavailable. It does
not publish the report, enable a backend or imply a supported release.

After copying, run python3 qualification/conference/packet/verify.py ARCHIVE.zip.
The standard-library checker reads without extracting, limits declared total size,
rejects duplicate/unexpected paths and JSON keys, and rechecks all manifest hashes.
This proves internal consistency only: a rewritten manifest can accompany altered
content. Publisher authenticity requires independently trusted source/revision or
signatures; the packet itself does not provide that authority.
