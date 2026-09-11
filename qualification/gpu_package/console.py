"""Recover complete console records; preserve strict conflicts and checksum checks."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_console", HERE.parent / "gpu_adapter/console.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def recover(text):
    complete = []
    truncated = []
    identity = None
    fragments = []
    full = {}
    for match in native.CHUNK.finditer(native.STAMP.sub("", text)):
        digest, index, count, part = match.groups()
        index, count = int(index), int(count)
        if not 1 <= count <= 128 or not 0 <= index < count or len(part) > 160:
            raise ValueError("chunk_bounds")
        if identity is not None and identity != (digest, count):
            raise ValueError("chunk_identity")
        identity = (digest, count)
        if index < count - 1 and len(part) != 160:
            truncated.append({"index": index, "length": len(part)})
            fragments.append((index, part))
            continue
        full[index] = part
        complete.append(f"QB_ADAPTER_CHUNK {digest} {index} {count} {part}")
    retained = "\n".join(complete) + "\n"
    report = native.decode(retained)
    if report is None:
        raise ValueError("complete_copy_missing")
    for index, fragment in fragments:
        if index not in full or not full[index].startswith(fragment):
            raise ValueError("truncated_copy_conflict")
    return report, retained, truncated
