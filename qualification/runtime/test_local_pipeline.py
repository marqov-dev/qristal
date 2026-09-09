import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from local_pipeline import run_local, PipelineError

PROGRAM=b'OPENQASM 2.0; include "qelib1.inc"; qreg r[2]; creg c[2]; x r[0]; measure r -> c;'
OPTIONS=b'{"qubits":2,"shots":17,"seed":42}'


class PipelineTests(unittest.TestCase):
    def test_options_reject_before_parse_or_process(self):
        invalid=[b'',b'x'*1025,b'\xff',b'[]',b'{"qubits":2,"shots":17}',
                 b'{"qubits":2,"shots":17,"seed":42,"extra":1}',
                 b'{"qubits":2,"qubits":2,"shots":17,"seed":42}']
        for key,value in [('qubits',True),('qubits',13),('shots',17.0),('shots',0),('seed',-1),('seed',float('nan'))]:
            invalid.append(json.dumps(json.loads(OPTIONS) | {key:value}).encode())
        with patch('local_pipeline.prepare') as parser,patch('local_pipeline.capture') as process:
            for options in invalid:
                with self.subTest(options=options[:60]),self.assertRaisesRegex(PipelineError,'^local_pipeline_rejected$'):
                    run_local(PROGRAM,options)
            parser.assert_not_called();process.assert_not_called()

    def test_invalid_program_never_starts_simulator(self):
        with patch('local_pipeline.capture') as process:
            with self.assertRaises(PipelineError):run_local(PROGRAM.replace(b'x r[0];',b'reset r[0];'),OPTIONS)
            process.assert_not_called()

    def test_output_failure_and_cleanup(self):
        paths=[]
        def failed(command, **kwargs):
            paths.append(Path(command[command.index('--qasm')+1]))
            self.assertTrue(paths[-1].exists())
            return 0,b'',b''
        with patch('local_pipeline.capture',side_effect=failed):
            with self.assertRaises(PipelineError):run_local(PROGRAM,OPTIONS)
        self.assertTrue(paths)
        self.assertTrue(all(not path.parent.exists() for path in paths))

    def test_real_roundtrip_and_hashes(self):
        for backend in ('qpp','aer'):
            with self.subTest(backend=backend):
                result=run_local(PROGRAM,OPTIONS,backend=backend)
                self.assertEqual(dict(result.result.counts),{'10':17})
                self.assertEqual(result.original_program_sha256,hashlib.sha256(PROGRAM).hexdigest())
                self.assertNotEqual(result.original_program_sha256,result.canonical_program_sha256)
                self.assertEqual(result.result.program_sha256,result.canonical_program_sha256)
                self.assertEqual(result.options_sha256,hashlib.sha256(OPTIONS).hexdigest())
                # A comment changes source identity without changing canonical semantics.
                second=run_local(PROGRAM+b' // changed source', OPTIONS+b' ',backend=backend)
                self.assertNotEqual(second.original_program_sha256,result.original_program_sha256)
                self.assertEqual(second.canonical_program_sha256,result.canonical_program_sha256)
                self.assertNotEqual(second.options_sha256,result.options_sha256)
                self.assertEqual(second.result.counts,result.result.counts)

if __name__=='__main__':unittest.main()
