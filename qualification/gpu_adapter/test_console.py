import base64
import hashlib
import json
import unittest
import zlib
from console import decode


def payload(data):
    raw = json.dumps(data).encode()
    blob = base64.b64encode(zlib.compress(raw)).decode()
    parts = [blob[i : i + 160] for i in range(0, len(blob), 160)]
    digest = hashlib.sha256(raw).hexdigest()
    return [
        f"QB_ADAPTER_CHUNK {digest} {i} {len(parts)} {p}" for i, p in enumerate(parts)
    ]


class ConsoleTests(unittest.TestCase):
    def test_duplicates_prefixes_and_annotations(self):
        lines = payload({"test": "abc" * 1000})
        text = "\n".join(lines + ["cloud-init: " + line for line in lines])
        text = text[:100] + "[2026-09-11T02:00:00.123456]" + text[100:]
        self.assertEqual(decode(text), {"test": "abc" * 1000})

    def test_incomplete(self):
        self.assertIsNone(decode("boot only"))
        self.assertIsNone(decode(payload({"test": list(range(500))})[0]))

    def test_modified_digest(self):
        line = payload({"test": 1})[0]
        parts = line.split()
        parts[1] = "0" * 64
        with self.assertRaisesRegex(ValueError, "payload_digest"):
            decode(" ".join(parts))

    def test_conflicting_duplicate(self):
        line = payload({"test": 1})[0]
        with self.assertRaises(ValueError):
            decode(line + "\n" + line[:-1] + "A")


if __name__ == "__main__":
    unittest.main()
