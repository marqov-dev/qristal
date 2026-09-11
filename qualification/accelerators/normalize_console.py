"""Remove only EC2-inserted ISO timestamp annotations from retained JSON payloads.

Two independently emitted copies must agree after normalization. This does not
repair counts or source hashes. Run check_evidence.py afterwards for those checks.
"""

import argparse
import json
from pathlib import Path
import re

ANNOTATION = re.compile(r"\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+\]")


def normalize(text):
    lines = text.splitlines()
    if len(lines) != 2:
        raise ValueError("two_console_copies_required")
    copies = [json.loads(ANNOTATION.sub("", line)) for line in lines]
    if copies[0] != copies[1]:
        raise ValueError("console_copies_disagree")
    return copies[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payloads", type=Path)
    args = parser.parse_args()
    print(json.dumps(normalize(args.payloads.read_text()), indent=2))
