import copy
import unittest
from fourier import MODES, reference, verify


def fixtures():
    return [{'qubits':n,'input':value,'mode':mode,'max_abs_error':0.0,
             'norm_error':abs(sum(abs(z)**2 for z in reference(n,value,mode))-1),
             'amplitudes':[[z.real,z.imag] for z in reference(n,value,mode)]}
            for n in range(1,4) for value in range(1<<n) for mode in MODES]


class FourierOracle(unittest.TestCase):
    def test_complete_exact_reference(self):
        self.assertEqual(verify(fixtures())['cases'],70)

    def test_missing_and_duplicate_cases(self):
        for records in (fixtures()[:-1], fixtures()+fixtures()[:1]):
            with self.assertRaises(ValueError): verify(records)

    def test_uniform_probabilities_with_wrong_phases_fail(self):
        records=fixtures()
        record=next(r for r in records if (r['qubits'],r['input'],r['mode'])==(3,1,'qft'))
        record['amplitudes']=[[abs(complex(*z)),0] for z in record['amplitudes']]
        with self.assertRaisesRegex(ValueError,'fourier_reference_mismatch'): verify(records)

    def test_conjugated_transform_or_reversed_order_fails(self):
        for change in ('sign','order'):
            records=fixtures()
            record=next(r for r in records if (r['qubits'],r['input'],r['mode'])==(3,1,'qft'))
            if change=='sign': record['amplitudes']=[[a,-b] for a,b in record['amplitudes']]
            else: record['amplitudes']=list(reversed(record['amplitudes']))
            with self.assertRaisesRegex(ValueError,'fourier_reference_mismatch'): verify(records)

    def test_nonfinite_and_false_error_metadata_fail(self):
        records=fixtures(); records[0]['amplitudes'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'wave_component'): verify(records)
        records=fixtures(); records[0]['max_abs_error']=0.5
        with self.assertRaisesRegex(ValueError,'error_metadata'): verify(records)
