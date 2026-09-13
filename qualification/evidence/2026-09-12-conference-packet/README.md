# Conference packet verification — 12 September 2026

The refreshed walkthrough and exporter at f3fb61adc87cf1b9c9bec46451ac0c8c51b116da
produced a self-contained five-chart HTML and ZIP with 24 allowlisted records.
All manifest hashes passed the independent standard-library archive verifier.
Static HTML inspection found five embedded PNGs and no remote rendering assets.

Browser security policy blocked opening the local file URL. No alternate serving
or browser workaround was attempted. Local-packet visual inspection and the final
human demonstration rehearsal remain open in platform #2172.

The existing Chrome profile loaded the saved Marqov report on UI build fff9303.
All five attached report images loaded; QFT, native drift and support-limitations
headings were present. This is a UI/content observation, not a hosted-job test.
The separate synthetic coverage chart is embedded in the offline packet and linked
from the report. No chart image or scientific result changed in this batch.

Use qualification/conference/packet/export.py and verify.py to reproduce a packet.
The recorded ZIP checksum identifies this export, not every later export (ZIP
metadata can differ). The manifest also records the exact source revision and
individual content hashes. The archive does not independently authenticate its
publisher. Temporary local download paths are not a permanent distribution channel.
