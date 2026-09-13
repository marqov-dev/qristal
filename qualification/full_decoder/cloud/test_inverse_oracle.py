import copy
import unittest
from inverse_oracle import expected,verify,MODES

def fixture():
    return [dict(layout=l,operation=o,mode=m,error=0,**({'amplitudes':[[v.real,v.imag] for v in expected(l,o)]} if m in ('inverse','fallback') else {})) for l in range(2) for o in range(10) for m in MODES]

class InverseOracle(unittest.TestCase):
    def test_inventory_and_norm(self):
        self.assertEqual(verify(fixture())['independently_replayed_vectors'],40)
        for l in range(2):
            for o in range(10):self.assertAlmostEqual(sum(abs(v)**2 for v in expected(l,o)),1)
    def test_global_phase_is_not_fitted_away(self):
        records=fixture()
        records[0]['amplitudes']=[[-x,-y] for x,y in records[0]['amplitudes']]
        with self.assertRaisesRegex(ValueError,'independent_phase_mismatch'):verify(records)
    def test_duplicate_case_rejected(self):
        records=fixture();records[-1]=copy.deepcopy(records[0])
        with self.assertRaisesRegex(ValueError,'case_inventory'):verify(records)
    def test_nonfinite_or_missing_vector_rejected(self):
        records=fixture();records[0]['amplitudes'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'nonfinite_state'):verify(records)
    def test_native_failures_not_hidden_by_reference_vectors(self):
        records=fixture();records[2]['error']=1e-3
        with self.assertRaisesRegex(ValueError,'native_error_bound'):verify(records)



from inverse_oracle import sparse_probabilities, verify_sparse
class SparseInverseOracle(unittest.TestCase):
    def test_independent_probabilities_normalized(self):
        for l in range(2):
            for o in range(10):self.assertAlmostEqual(sum(sparse_probabilities(l,o)),1)
    def test_incorrect_sparse_counts_rejected(self):
        records=[]
        for l in range(2):
            for o in range(10):
                probabilities=sparse_probabilities(l,o)
                counts=[int(p*16384) for p in probabilities]
                counts[counts.index(max(counts))]+=16384-sum(counts)
                records.append(dict(layout=l,operation=o,counts=counts))
        self.assertEqual(verify_sparse(records)['cases'],20)
        records[0]['counts']=[16384]+[0]*(len(records[0]['counts'])-1)
        with self.assertRaisesRegex(ValueError,'sparse_phase_mismatch'):verify_sparse(records)



class LegacyClassification(unittest.TestCase):
    def test_global_phase_mismatch_remains_a_failure(self):
        records=fixture()
        legacy=next(row for row in records if row['layout']==0 and row['operation']==0 and row['mode']=='fallback')
        legacy['amplitudes']=[[-x,-y] for x,y in legacy['amplitudes']]
        legacy['error']=max(2*abs(v) for v in expected(0,0))
        report=verify(records)
        self.assertEqual(report['legacy_mismatches'],1)
        row=report['legacy_observations'][0]
        self.assertFalse(row['matches_exact_oracle'])
        self.assertLess(row['diagnostic_phase_aligned_error'],1e-10)
    def test_legacy_error_cannot_be_hidden(self):
        records=fixture()
        legacy=next(row for row in records if row['mode']=='fallback')
        legacy['error']=.1
        with self.assertRaisesRegex(ValueError,'legacy_error_binding'):verify(records)

if __name__=='__main__':unittest.main()
