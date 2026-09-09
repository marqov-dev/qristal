"""Run in the existing CPU image's Qiskit environment."""
import hashlib
import unittest
from program_guard import prepare, ProgramError

HEADER='OPENQASM 2.0; include "qelib1.inc"; '
BASE=HEADER+'qreg r[2]; creg b[2]; '


class ProgramTests(unittest.TestCase):
    def test_canonical_and_original(self):
        raw=(BASE+'h r[0]; cx r[0],r[1]; measure r -> b; // comment').encode()
        result=prepare(raw,2)
        self.assertEqual(result.original_sha256,hashlib.sha256(raw).hexdigest())
        self.assertIn(b'h q[0];\ncx q[0],q[1];',result.canonical)
        self.assertEqual(prepare(result.canonical,2).canonical,result.canonical)
        expanded=(BASE+'measure r[0] -> b[0]; measure r[1] -> b[1];').encode()
        self.assertEqual(prepare(expanded,2).canonical,prepare((BASE+'measure r -> b;').encode(),2).canonical)

    def test_reject_semantics(self):
        suffixes=['x r[0];', 'measure r[0] -> b[0];',
          'measure r[0] -> b[1]; measure r[1] -> b[0];',
          'measure r[1] -> b[1]; measure r[0] -> b[0];',
          'measure r -> b; x r[0];',
          'measure r[0] -> b[0]; x r[0]; measure r -> b;',
          'reset r[0]; measure r -> b;',
          'if(b==0) x r[0]; measure r -> b;',
          'barrier r; measure r -> b;',
          'rx(0.5) r[0]; measure r -> b;',
          'z r[0]; measure r -> b;',
          'cx r[0],r[0]; measure r -> b;',
          'x r[2]; measure r -> b;',
          'opaque mystery a; mystery r[0]; measure r -> b;',
          'gate custom a { x a; } custom r[0]; measure r -> b;']
        for suffix in suffixes:
            with self.subTest(suffix=suffix),self.assertRaisesRegex(ProgramError,'^program_rejected$'):
                prepare((BASE+suffix).encode(),2)

    def test_bounds_and_registers(self):
        for n in (1,12):
            raw=(HEADER+f'qreg q[{n}]; creg c[{n}]; x q[0]; measure q -> c;').encode()
            self.assertEqual(prepare(raw,n).qubits,n)
        invalid=[(BASE+'measure r -> b;').replace('b[2]','b[3]'),
                 BASE+'creg other[1]; measure r -> b;',
                 BASE+'qreg other[1]; measure r -> b;',
                 BASE+'include "/tmp/secret"; measure r -> b;',
                 BASE+'x r[0];'*4095+'measure r -> b;']
        for raw in invalid:
            with self.subTest(prefix=raw[:60]),self.assertRaises(ProgramError):prepare(raw.encode(),2)
        for n in (True,0,13):
            with self.assertRaises(ProgramError):prepare((BASE+'measure r -> b;').encode(),n)

if __name__=='__main__':unittest.main()
