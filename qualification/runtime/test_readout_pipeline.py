"""Boundary/failure checks; native analytic matrix is readout_demo.py."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from local_pipeline import run_local, run_readout, PipelineError
from readout_demo import program, settings, check, SHOTS


class ReadoutTests(unittest.TestCase):
    def test_rejects_options_before_parser_or_simulator(self):
        valid = json.loads(settings(.2, .1))
        invalid = [b'', b'x'*1025, b'[]', b'null', b'\xff',
                   b'{"qubits":2,"shots":17,"seed":42,"readout":{"p10":0,"p10":1,"p01":0}}']
        for noise in (None, [], {}, {'p10': .2}, {'p10': .2, 'p01': .1, 'qubit': 1}):
            invalid.append(json.dumps(valid | {'readout': noise}).encode())
        for key in ('p10', 'p01'):
            for bad in (-.1, 1.1, True, '0.2', None, float('nan'), float('inf')):
                invalid.append(json.dumps(valid | {'readout': valid['readout'] | {key: bad}}).encode())
        for key, bad in [('qubits', True), ('qubits', 13), ('shots', 0),
                         ('shots', 16385), ('seed', -1), ('seed', 2**31)]:
            invalid.append(json.dumps(valid | {key: bad}).encode())
        invalid += [json.dumps(valid | {'backend': 'qpp'}).encode(),
                    json.dumps({k: v for k, v in valid.items() if k != 'readout'}).encode()]
        with patch('local_pipeline.prepare') as parser, patch('local_pipeline.capture') as process:
            for value in invalid:
                with self.subTest(value=value[:80]), self.assertRaisesRegex(PipelineError, '^local_pipeline_rejected$'):
                    run_readout(program(''), value)
            parser.assert_not_called()
            process.assert_not_called()

    def test_ideal_entrypoint_does_not_accept_noise(self):
        with patch('local_pipeline.prepare') as parser:
            for backend in ('qpp', 'aer'):
                with self.assertRaises(PipelineError):
                    run_local(program(''), settings(.2, .1), backend=backend)
            parser.assert_not_called()

    def test_rejected_circuit_cannot_reach_native_engine(self):
        with patch('local_pipeline.capture') as process:
            for gates in ('reset q[0];', 'rx(.2) q[0];', 'barrier q;'):
                with self.assertRaises(PipelineError):
                    run_readout(program(gates), settings(.2, .1))
            process.assert_not_called()

    def test_exact_cli_settings_hashes_and_file_cleanup(self):
        source = program('x q[0];')
        options = settings(.2, .1) + b' '
        paths = []
        def capture(command, **kwargs):
            self.assertEqual(kwargs, {'timeout': 60})
            self.assertEqual(command[command.index('--backend')+1], 'aer')
            self.assertEqual(command[command.index('--readout-p10')+1], '0.2')
            self.assertEqual(command[command.index('--readout-p01')+1], '0.1')
            path = Path(command[command.index('--qasm')+1])
            paths.append(path)
            payload = {'interface': 'local-qristal-sample/experimental',
                       'program_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'backend': 'aer', 'shots': SHOTS, 'bit_order': 'qubit_0_first',
                       'counts': {'10': SHOTS}}
            return 0, json.dumps(payload).encode(), b''
        with patch('local_pipeline.capture', side_effect=capture):
            result = run_readout(source, options)
        self.assertEqual(result.options_sha256, hashlib.sha256(options).hexdigest())
        self.assertTrue(paths)
        self.assertTrue(all(not p.parent.exists() for p in paths))

    def test_process_and_candidate_failures_do_not_fall_back(self):
        for failure in ('timeout', 'stderr', 'wrong-backend', 'nonzero'):
            calls = []
            def capture(command, **kwargs):
                calls.append(command)
                if failure == 'timeout':
                    raise RuntimeError('timeout')
                path = Path(command[command.index('--qasm')+1])
                payload = {'interface': 'local-qristal-sample/experimental',
                           'program_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'backend': 'qpp' if failure == 'wrong-backend' else 'aer',
                           'shots': SHOTS, 'bit_order': 'qubit_0_first', 'counts': {'00': SHOTS}}
                return (2 if failure == 'nonzero' else 0), json.dumps(payload).encode(), (b'bad' if failure == 'stderr' else b'')
            with self.subTest(failure=failure), patch('local_pipeline.capture', side_effect=capture):
                with self.assertRaises(PipelineError):
                    run_readout(program(''), settings(.2, .1))
            self.assertEqual(len(calls), 1)
            path = Path(calls[0][calls[0].index('--qasm')+1])
            self.assertFalse(path.parent.exists())

    def test_declared_tolerances_detect_wrong_noise_and_bit_order(self):
        check({'00': SHOTS}, {'00': 1})
        for actual, expected in [({'00': SHOTS-1, '10': 1}, {'00': 1}),
                                 ({'01': SHOTS}, {'10': 1}),
                                 ({'00': SHOTS}, {'00': .8, '10': .2})]:
            with self.assertRaises(ValueError):
                check(actual, expected)


if __name__ == '__main__':
    unittest.main()
