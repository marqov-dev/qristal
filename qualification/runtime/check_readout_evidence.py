"""Offline consistency check; hashes are not signatures or hosted attestation."""
import argparse
import json
from pathlib import Path
import re

from qualify_readout_image import FILES, HERE, IMAGE, sha

DEFAULT = HERE.parent / 'evidence/2026-09-11-readout-pipeline'


def verify(directory):
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    expected_files = {f'{stage}{suffix}' for stage in ('tests', 'demo')
                      for suffix in ('.stdout', '.stderr', '-intent.json', '-cleanup.json')}
    if (manifest['parent_image'] != IMAGE or set(manifest['files']) != expected_files
            or manifest['native_rebuild'] is not False
            or manifest['registry_published'] is not False or manifest['cloud_execution'] is not False):
        raise ValueError('manifest_scope_changed')
    for name, expected in manifest['files'].items():
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError('evidence_changed')
    if manifest['overlay_sources'] != {name: sha((HERE / name).read_bytes()) for name in FILES}:
        raise ValueError('overlay_changed')
    if manifest['harness_sha256'] != sha((HERE / 'qualify_readout_image.py').read_bytes()):
        raise ValueError('harness_changed')
    if (directory / 'demo.stderr').read_bytes() or (directory / 'tests.stdout').read_bytes():
        raise ValueError('unexpected_output')
    if not re.search(rb'Ran 27 tests in [0-9.]+s\s+OK\s*$', (directory / 'tests.stderr').read_bytes()):
        raise ValueError('test_result_changed')
    for stage in ('tests', 'demo'):
        intent = json.loads((directory / f'{stage}-intent.json').read_bytes())
        cleanup = json.loads((directory / f'{stage}-cleanup.json').read_bytes())
        if (intent['image'] != IMAGE or not re.fullmatch(r'qristal-readout-[a-f0-9]{32}', intent['name'])
                or cleanup != {'name': intent['name'], 'absent': True}):
            raise ValueError('cleanup_changed')
    report = json.loads((directory / 'demo.stdout').read_bytes())
    if report['shots'] != 16384 or report['absolute_tolerance'] != .025:
        raise ValueError('statistical_policy_changed')
    cases = {
        'ideal-zero': ('', 0, 0, 42, {'00': 1}),
        'ideal-one': ('x q[0];', 0, 0, 42, {'10': 1}),
        'flip-zero': ('', 1, 1, 42, {'10': 1}),
        'flip-one': ('x q[0];', 1, 1, 42, {'00': 1}),
        'qubit-one-preserved': ('x q[1];', 1, 1, 42, {'11': 1}),
    }
    for seed in (7, 42):
        cases.update({
            f'asymmetric-zero-seed{seed}': ('', .2, .1, seed, {'00': .8, '10': .2}),
            f'asymmetric-one-seed{seed}': ('x q[0];', .2, .1, seed, {'00': .1, '10': .9}),
            f'asymmetric-bell-seed{seed}': ('h q[0]; cx q[0],q[1];', .2, .1, seed,
                                          {'00': .4, '10': .1, '01': .05, '11': .45}),
        })
    fixtures = report['fixtures']
    if len(fixtures) != len(cases) or {r['label'] for r in fixtures} != set(cases):
        raise ValueError('fixture_matrix_changed')
    for result in fixtures:
        gates, p10, p01, seed, expected = cases[result['label']]
        program = (f'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; '
                   f'{gates} measure q -> c;')
        options = {'qubits': 2, 'shots': 16384, 'seed': seed, 'readout': {'p10': p10, 'p01': p01}}
        # Independent canonical output for these fixed X/H/CX fixtures only.
        body = [g.strip() + ';' for g in gates.split(';') if g.strip()]
        canonical = '\n'.join(['OPENQASM 2.0;', 'include "qelib1.inc";', 'qreg q[2];',
                               'creg c[2];', *body, 'measure q -> c;', ''])
        if (result['program'] != program or result['original_sha256'] != sha(program.encode())
                or result['canonical_sha256'] != sha(canonical.encode())
                or result['options'] != options or result['options_bytes'] != json.dumps(options, sort_keys=True)
                or result['options_sha256'] != sha(result['options_bytes'].encode())
                or result['expected_probabilities'] != expected or result['backend'] != 'aer'):
            raise ValueError('fixture_binding_changed')
        counts = result['counts']
        if (not set(counts) <= set(expected) or sum(counts.values()) != 16384
                or any(type(v) is not int or v <= 0 for v in counts.values())):
            raise ValueError('invalid_counts')
        for bits, probability in expected.items():
            tolerance = 0 if probability in (0, 1) else .025
            if abs(counts.get(bits, 0) / 16384 - probability) > tolerance:
                raise ValueError('probability_mismatch')
    return {'status': 'verified', 'tests': 27, 'analytic_fixtures': 11, 'execution': 'none'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=DEFAULT)
    print(json.dumps(verify(parser.parse_args().directory), sort_keys=True))
