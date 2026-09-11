"""Fixed analytic demo. Run only inside the bounded CPU image via qualification harness."""
import hashlib
import json
from local_pipeline import run_readout

SHOTS = 16384
TOLERANCE = 0.025  # Declared before execution; deterministic endpoints require exact counts.


def program(gates, qubits=2):
    return (f'OPENQASM 2.0; include "qelib1.inc"; qreg q[{qubits}]; '
            f'creg c[{qubits}]; {gates} measure q -> c;').encode()


def settings(p10, p01, seed=42):
    return json.dumps({'qubits': 2, 'shots': SHOTS, 'seed': seed,
                       'readout': {'p10': p10, 'p01': p01}}, sort_keys=True).encode()


def check(counts, expected):
    if (sum(counts.values()) != SHOTS or not set(counts) <= set(expected)
            or any(type(v) is not int or v <= 0 for v in counts.values())):
        raise ValueError('readout_counts_rejected')
    for bits, probability in expected.items():
        tolerance = 0 if probability in (0, 1) else TOLERANCE
        if abs(counts.get(bits, 0) / SHOTS - probability) > tolerance:
            raise ValueError('readout_probability_rejected')


def demonstrate():
    records = []
    fixtures = [
        ('ideal-zero', '', 0, 0, {'00': 1}),
        ('ideal-one', 'x q[0];', 0, 0, {'10': 1}),
        ('flip-zero', '', 1, 1, {'10': 1}),
        ('flip-one', 'x q[0];', 1, 1, {'00': 1}),
        ('qubit-one-preserved', 'x q[1];', 1, 1, {'11': 1}),
    ]
    for seed in (7, 42):
        for label, gates, expected in [
            ('asymmetric-zero', '', {'00': .8, '10': .2}),
            ('asymmetric-one', 'x q[0];', {'00': .1, '10': .9}),
            ('asymmetric-bell', 'h q[0]; cx q[0],q[1];',
             {'00': .4, '10': .1, '01': .05, '11': .45}),
        ]:
            fixtures.append((f'{label}-seed{seed}', gates, .2, .1, expected, seed))
    for fixture in fixtures:
        label, gates, p10, p01, expected, *seed = fixture
        raw_program = program(gates)
        raw_options = settings(p10, p01, seed[0] if seed else 42)
        observation = run_readout(raw_program, raw_options)
        if (observation.result.backend != 'aer'
                or observation.original_program_sha256 != hashlib.sha256(raw_program).hexdigest()
                or observation.options_sha256 != hashlib.sha256(raw_options).hexdigest()
                or observation.result.program_sha256 != observation.canonical_program_sha256):
            raise ValueError('readout_binding_rejected')
        actual = dict(observation.result.counts)
        check(actual, expected)
        records.append({'label': label, 'program': raw_program.decode(),
                        'options': json.loads(raw_options), 'options_bytes': raw_options.decode(),
                        'original_sha256': observation.original_program_sha256,
                        'canonical_sha256': observation.canonical_program_sha256,
                        'options_sha256': observation.options_sha256,
                        'backend': observation.result.backend, 'counts': actual,
                        'expected_probabilities': expected})
    return {'profile': 'restricted-cpu-readout-demo-v0', 'shots': SHOTS,
            'absolute_tolerance': TOLERANCE, 'fixtures': records,
            'scope': 'local Aer readout on qubit zero; no hosted or commercial capability'}


if __name__ == '__main__':
    print(json.dumps(demonstrate(), sort_keys=True))
