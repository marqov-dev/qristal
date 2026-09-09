"""Pure adapter conformance; no Qristal dependency or service required."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest
from adapter import SampleError, encode_result, read_program, sample, validate_options, validate_program

PROGRAM = b'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[0]; measure q -> c;'

class AdapterTests(unittest.TestCase):
    def test_options(self):
        defaults = dict(backend='qpp', qubits=2, shots=4096, seed=42, p10=0., p01=0.)
        for key, values in dict(backend=['gpu', None], qubits=[0,13,True], shots=[0,16385,True], seed=[-1,2**31,True], p10=[-1,1.1,float('nan'),float('inf'),True], p01=[-1,1.1]).items():
            for value in values:
                with self.subTest(key=key,value=value), self.assertRaises(SampleError):
                    validate_options(**(defaults | {key:value}))
        for qubits, shots, seed in [(1,1,0),(12,16384,2**31-1)]:
            validate_options('qpp',qubits,shots,seed,0,0)
        validate_options('aer',2,10,0,1,1)
        with self.assertRaises(SampleError): validate_options('qpp',2,10,0,.1,0)

    def test_programs(self):
        validate_program(PROGRAM,2)
        validate_program(b'// unicode comment: \xc3\xa9\n' + PROGRAM + b'/* include "bad"; qreg f[5]; */',2)
        invalid = [b'', b'x'*65537, b'\xff', PROGRAM.replace(b'2.0',b'3.0'), PROGRAM.replace(b'"qelib1.inc"',b'"/tmp/private"'), PROGRAM.replace(b'include',b'// include') , PROGRAM+b'include "qelib1.inc";', PROGRAM+b'qreg r[2];', PROGRAM.replace(b'q[2]',b'q[3]'), PROGRAM+b'/*', PROGRAM+b'"hidden"']
        for data in invalid:
            with self.subTest(data=data[:80]), self.assertRaises(SampleError): validate_program(data,2)
        # Rejection must happen before importing the unavailable native module.
        with self.assertRaisesRegex(SampleError,'program_size'): sample(b'')

    def test_counts_and_hash(self):
        result=json.loads(encode_result(PROGRAM,'qpp',2,7,{(True,False):7}))
        self.assertEqual(result['counts'],{'10':7})
        self.assertEqual(result['program_sha256'],hashlib.sha256(PROGRAM).hexdigest())
        self.assertEqual(result['bit_order'],'qubit_0_first')
        for raw in [{(True,):7},{(1,0):7},{(True,False):True},{(True,False):-1},{(True,False):7.0},{(True,False):6},{}]:
            with self.subTest(raw=raw), self.assertRaises(SampleError): encode_result(PROGRAM,'qpp',2,7,raw)
        raw={key:4 for key in itertools.product((False,True),repeat=12)}
        self.assertLess(len(encode_result(PROGRAM,'qpp',12,16384,raw)),131072)

    def test_files(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'program';p.write_bytes(PROGRAM)
            self.assertEqual(read_program(p),PROGRAM)
            link=Path(directory)/'link';link.symlink_to(p)
            fifo=Path(directory)/'fifo';os.mkfifo(fifo)
            for bad in [link,fifo,Path(directory),None]:
                with self.subTest(path=bad), self.assertRaises(SampleError): read_program(bad)
            p.write_bytes(b'x'*65537)
            with self.assertRaises(SampleError): read_program(p)

if __name__ == '__main__': unittest.main()
