import itertools
import json
import hashlib
import unittest
from candidate import CandidateError, validate_candidate

PROGRAM = b'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; x q[0]; measure q -> c;'


def record():
    return dict(interface='local-qristal-sample/experimental',
                program_sha256=hashlib.sha256(PROGRAM).hexdigest(), backend='qpp',
                shots=17, bit_order='qubit_0_first', counts={'10':17})


def check(raw, **overrides):
    args=dict(returncode=0, program=PROGRAM, backend='qpp', qubits=2, shots=17)
    return validate_candidate(raw, **(args | overrides))


class CandidateTests(unittest.TestCase):
    def test_valid_mapping(self):
        value=check(json.dumps(record()).encode()+b'\n')
        self.assertEqual(value.counts,(('10',17),))
        self.assertEqual(value.logical_bits,('q[0]','q[1]'))

    def test_changed_fields(self):
        for key, value in [('interface','other'),('program_sha256','a'*64),('backend','aer'),
                           ('shots',16),('shots',True),('shots',17.0),('bit_order','reverse'),
                           ('counts',{'10':16}),('counts',{'10':True}),('counts',{'10':17.0}),
                           ('counts',{'10':-1}),('counts',{'10':0}),('counts',{'1':17}),
                           ('counts',{'xx':17}),('counts',{}),('counts',[]),('extra','value')]:
            with self.subTest(key=key,value=value), self.assertRaisesRegex(CandidateError,'^candidate_rejected$'):
                check(json.dumps(record() | {key:value}).encode())
        for key in record():
            obj=record();del obj[key]
            with self.assertRaises(CandidateError):check(json.dumps(obj).encode())

    def test_malformed_wire(self):
        raw=json.dumps(record()).encode()
        for bad in [b'',b'\xff',b'[]',raw+b'\n\n',raw+b'{}',b' '+raw,raw+b' ',
                    b'{'*2000+b'}'*2000,b'x'*131074,
                    raw.replace(b'"shots": 17',b'"shots":17,"shots":17'),
                    raw.replace(b'"10": 17',b'"10":17,"10":17'),
                    raw.replace(b'"10": 17',b'"10":NaN'),
                    raw.replace(b'"10": 17',b'"10":Infinity')]:
            with self.subTest(prefix=bad[:30]),self.assertRaises(CandidateError):check(bad)

    def test_expected_facts_and_exit(self):
        raw=json.dumps(record()).encode()
        for args in [dict(returncode=1),dict(returncode=-9),dict(returncode=False),
                     dict(program=PROGRAM+b' '),dict(program=b''),dict(backend='aer'),
                     dict(qubits=1),dict(qubits=True),dict(shots=18),dict(shots=True)]:
            with self.subTest(args=args),self.assertRaises(CandidateError):check(raw,**args)

    def test_maximum_outcomes(self):
        obj=record() | {'shots':16384,'counts':{''.join(bits):4 for bits in itertools.product('01',repeat=12)}}
        value=check(json.dumps(obj).encode(),qubits=12,shots=16384)
        self.assertEqual(len(value.counts),4096)

if __name__ == '__main__':unittest.main()
