"""Check consistency of synthetic microVM test evidence; never execute a guest."""
import argparse
import hashlib
import json
from pathlib import Path
import re

MODES = ('prepare', 'validate', 'simulate', 'killed', 'overflow')
PROGRAM = b'OPENQASM 2.0; include "qelib1.inc"; qreg r[2]; creg b[2]; x r[0]; measure r -> b;'
OPTIONS = b'{"qubits":2,"shots":17,"seed":42}'
CANONICAL = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nx q[0];\nmeasure q -> c;\n'


def require(value, message):
    if not value:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def read(path, limit):
    require(not path.is_symlink(), 'symlink evidence')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'evidence exceeds size bound')
    return data


def marker(lines, prefix):
    matches = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    require(len(matches) == 1, 'missing or duplicate ' + prefix)
    return decode(matches[0])


def check(directory):
    directory = Path(directory)
    report = decode(read(directory / 'report.json', 32768))
    require(report.get('passed') is True, 'report did not pass')
    require(report.get('synthetic_data_only') is True, 'not synthetic')
    require(report.get('guest_credentials') is False, 'guest credentials')
    runs = report['runs']
    require([row['mode'] for row in runs] == list(MODES), 'incomplete or reordered cases')
    for field in ('guest_id', 'launch_operation', 'guest_generation'):
        require(len({row[field] for row in runs}) == len(MODES), 'reused ' + field)
    for row in runs:
        guest = row['guest_id']
        require(re.fullmatch(r'qb-[0-9a-f]{12}', guest), 'invalid guest id')
        require(row['supervisor_epoch'] == report['supervisor_epoch'], 'epoch mismatch')
        require(row['stop_observed'] is True, 'termination not observed')
        console = read(directory / (guest + '.console'), 131073 + 4096)
        require(len(console) == row['console_bytes'], 'console length mismatch')
        lines = console.decode('utf-8', errors='strict').splitlines()
        observed = marker(lines, 'QB_ISOLATION=')
        require(type(observed['uid']) is int and observed['uid'] == 65532, 'guest UID')
        require(observed['interfaces'] == ['lo'], 'guest interfaces')
        for flag in ('canary_absent', 'management_socket_absent',
                     'metadata_unreachable', 'aws_environment_absent'):
            require(observed[flag] is True, 'isolation observation: ' + flag)
        mode = row['mode']
        if mode in ('killed', 'overflow'):
            reason = 'requested_kill' if mode == 'killed' else 'output_limit'
            require(row['reason'] == reason and row['exit'] == -9, 'failed stop case')
            if mode == 'killed':
                require('QB_WAITING' in lines, 'kill before waiting marker')
            else:
                require(len(console) > 131073, 'no output overflow')
            continue
        require(row['reason'] == 'guest_completed' and row['exit'] in (0, -9), 'completion')
        require(lines.count('QB_EXIT=0') == 1, 'completion marker')
        result = marker(lines, 'QB_RESULT=')
        for key, data in [('original_sha256', PROGRAM), ('options_sha256', OPTIONS),
                          ('canonical_sha256', CANONICAL.encode())]:
            require(result[key] == hashlib.sha256(data).hexdigest(), 'binding: ' + key)
        require(result['canonical'] == CANONICAL, 'canonical program')
        require(result['logical_bits'] == ['q[0]', 'q[1]'], 'logical bits')
        if mode == 'simulate':
            require(result['counts'] == {'10': 17}, 'basis counts')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    check(args.directory)
    print('PASS: five synthetic cases are internally consistent; not authenticated execution proof')
