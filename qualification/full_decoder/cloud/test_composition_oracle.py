import copy
import unittest
from composition_oracle import verify_states, verify_inventory

class CompositionTests(unittest.TestCase):
    def states(self):
        return [dict(route=r,angle=a,amplitudes=[[0,0],[1,0]]+[[0,0]]*6,outer_one_probability=0)
                for r in ('candidate','legacy') for a in (.37,-.37,.9,-.9)]
    def test_complete(self): self.assertEqual(verify_states(self.states())['candidate_cases'],4)
    def test_missing(self):
        with self.assertRaisesRegex(ValueError,'case_inventory'): verify_states(self.states()[:-1])
    def test_duplicate(self):
        s=self.states();s[-1]=s[0]
        with self.assertRaisesRegex(ValueError,'case_inventory'): verify_states(s)
    def test_nonfinite(self):
        s=self.states();s[0]['amplitudes'][0]=[float('nan'),0]
        with self.assertRaisesRegex(ValueError,'nonfinite'): verify_states(s)
    def test_probability_tamper(self):
        s=self.states();s[0]['outer_one_probability']=.1
        with self.assertRaisesRegex(ValueError,'probability_binding'): verify_states(s)
    def test_candidate_failure(self):
        s=self.states();s[0]['amplitudes']=[[0,0]]*8;s[0]['amplitudes'][5]=[1,0];s[0]['outer_one_probability']=1
        with self.assertRaisesRegex(ValueError,'candidate_interference'): verify_states(s)
    def test_legacy_diagnostic(self):
        s=self.states();s[-1]['amplitudes']=[[0,0]]*8;s[-1]['amplitudes'][5]=[1,0];s[-1]['outer_one_probability']=1
        self.assertEqual(verify_states(s)['observations'][-1]['outer_one_probability'],1)
    def inventory(self):
        root=dict(kind='preparation',index=0,nodes=2,primitive_leaves=1,eligible_control_blocks=0,estimated_sparse_visits=2,composite_names={'root':1})
        child=dict(kind='child',index=0,nodes=1,primitive_leaves=1,eligible_control_blocks=0,estimated_sparse_visits=1,composite_names={})
        inverse=copy.deepcopy(root);inverse['kind']='legacy_inverse'
        return [root,child,inverse]
    def test_inventory(self): self.assertEqual(verify_inventory(self.inventory())['top_level_children'],1)
    def test_inventory_mismatch(self):
        rows=self.inventory();rows[0]['nodes']=3;rows[0]['composite_names']['root']=2
        with self.assertRaisesRegex(ValueError,'child_accounting'):verify_inventory(rows)
    def test_inventory_bounds(self):
        rows=self.inventory();rows[0]['nodes']=1000001
        with self.assertRaisesRegex(ValueError,'inventory_bound'):verify_inventory(rows)

if __name__=='__main__':unittest.main()
