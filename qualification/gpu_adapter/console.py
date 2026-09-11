"""Reassemble bounded, checksummed qualification console chunks; no runtime calls."""

import base64
import hashlib
import json
import re
import zlib

STAMP = re.compile(r"\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+\]")
CHUNK = re.compile(r"QB_ADAPTER_CHUNK ([a-f0-9]{64}) (\d+) (\d+) ([A-Za-z0-9+/=]+)")


def decode(text):
    pieces = {}
    identity = None
    total = None
    for match in CHUNK.finditer(STAMP.sub("", text)):
        digest, index, count, part = match.groups()
        index, count = int(index), int(count)
        if not 1 <= count <= 128 or not 0 <= index < count or len(part) > 160:
            raise ValueError("chunk_bounds")
        if identity is not None and (identity != digest or total != count):
            raise ValueError("chunk_identity")
        identity, total = digest, count
        if index in pieces and pieces[index] != part:
            raise ValueError("chunk_conflict")
        pieces[index] = part
    if total is None or len(pieces) != total:
        return None
    compressed = base64.b64decode(
        "".join(pieces[i] for i in range(total)), validate=True
    )
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(compressed, 131073)
    if len(raw) > 131072 or not decompressor.eof or decompressor.unused_data:
        raise ValueError("payload_bounds")
    if hashlib.sha256(raw).hexdigest() != identity:
        raise ValueError("payload_digest")
    return json.loads(raw)
