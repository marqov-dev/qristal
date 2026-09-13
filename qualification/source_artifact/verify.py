"""Offline CLI; verifies only, never extracts or executes artifact members."""
import argparse
import json
from pathlib import Path
from archive import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('recovered', type=Path)
    args = parser.parse_args()
    recovered = json.loads(args.recovered.read_text())
    report = recovered.get('result', recovered)
    identity = report['output_artifact']
    original = {k: v for k, v in report.items() if k != 'output_artifact'}
    print(json.dumps(verify(args.archive, identity, original), sort_keys=True))


if __name__ == '__main__':
    main()
