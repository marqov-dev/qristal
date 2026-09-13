import unittest
from mcz_oracle import wave, verify_states, verify_sparse, LAYOUTS, MODES, sparse_inventory

class IndependentOracle(unittest.TestCase):
    def fixtures(self):
        records=[]
        for index in range(len(LAYOUTS)):
            for mode in MODES:
                n,controls,target,values=wave(index,mode)
                records.append(dict(layout=index,mode=mode,qubits=n,controls=list(controls),target=target,
                                    amplitudes=[[v.real,v.imag] for v in values]))
        return records

    def test_inventories(self):
        self.assertEqual(verify_states(self.fixtures())['cases'],42)
        records=[dict(controls=k,pattern=p,mode=m,counts=c) for (k,p,m),c in sparse_inventory().items()]
        self.assertEqual(verify_sparse(records)['cases'],158)

    def test_global_phase_is_not_fitted_away(self):
        records=self.fixtures()
        records[0]['amplitudes']=[[-r,-i] for r,i in records[0]['amplitudes']]
        with self.assertRaisesRegex(ValueError,'state_phase_or_norm'):verify_states(records)

    def test_duplicate_cannot_replace_missing_layout(self):
        records=self.fixtures();records[-1]=records[0]
        with self.assertRaisesRegex(ValueError,'state_inventory'):verify_states(records)

    def test_probability_only_match_is_insufficient(self):
        records=self.fixtures()
        records[0]['amplitudes']=[[abs(complex(r,i)),0] for r,i in records[0]['amplitudes']]
        with self.assertRaisesRegex(ValueError,'state_phase_or_norm'):verify_states(records)

    def test_interference_target_bit_is_required(self):
        records=[dict(controls=k,pattern=p,mode=m,counts=c) for (k,p,m),c in sparse_inventory().items()]
        records[-1]['counts']={'0'*19:64}
        with self.assertRaisesRegex(ValueError,'sparse_interference'):verify_sparse(records)

if __name__=='__main__':unittest.main()
