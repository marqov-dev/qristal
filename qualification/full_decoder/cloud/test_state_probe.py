import json
import unittest
from instrument_state import header,visitor,derive
from state_probe_analysis import parse, backend_durations

class ProbeTests(unittest.TestCase):
    def test_source_changes_rejected(self):
        for fn in (header,visitor):
            with self.assertRaisesRegex(ValueError,'source_identity'):fn(b'changed')
    def test_reversible_addition(self):
        import hashlib
        raw=b'prefix anchor suffix'
        changed=derive(raw,hashlib.sha256(raw).hexdigest(),[('anchor','observation')])
        self.assertEqual(changed,b'prefix // QB_STATE_BEGIN\nobservation\n// QB_STATE_END\nanchor suffix')
    def test_ambiguous_anchor_rejected(self):
        import hashlib
        raw=b'aa'
        with self.assertRaisesRegex(ValueError,'probe_anchor'):derive(raw,hashlib.sha256(raw).hexdigest(),[('a','probe')])
    def line(self,event='begin',nodes=0,time=0):
        return 'SPARSE_STATE '+json.dumps(dict(event=event,phase=0,nodes=nodes,elapsed_us=time,states=1,operations=0,h=0,rx=0,ry=0))
    def test_timeout_keeps_incomplete(self):
        result,_=parse(self.line()+'\n'+self.line('sample',8192,10))
        self.assertFalse(result[0]['sampling_completed'])
    def test_backend_timing_pairs(self):
        output='SEARCH_TRACE backend_execute_begin elapsed_ms=2\nSEARCH_TRACE backend_execute_end elapsed_ms=9\nSEARCH_TRACE backend_execute_begin elapsed_ms=10'
        self.assertEqual(backend_durations(output),{'completed_call_ms':[7],'incomplete_call_started':True})
    def test_backend_end_requires_start(self):
        with self.assertRaisesRegex(ValueError,'backend_pair'):backend_durations('SEARCH_TRACE backend_execute_end elapsed_ms=9')
    def test_sampling_pair(self):
        result,_=parse(self.line()+'\n'+self.line('sample_begin',8193,11)+'\n'+self.line('sample_end',8193,12))
        self.assertTrue(result[0]['sampling_completed'])
    def test_missing_begin(self):
        with self.assertRaisesRegex(ValueError,'missing_begin'):parse(self.line('sample',8192,10))
    def test_invalid_interval(self):
        with self.assertRaisesRegex(ValueError,'sample_interval'):parse(self.line()+'\n'+self.line('sample',8193,10))
    def test_nonmonotonic(self):
        with self.assertRaisesRegex(ValueError,'nonmonotonic'):parse(self.line()+'\n'+self.line('sample',8192,10)+'\n'+self.line('sample',8192,9))
    def test_end_without_begin(self):
        with self.assertRaisesRegex(ValueError,'sampling_pair'):parse(self.line()+'\n'+self.line('sample_end',8192,10))

if __name__=='__main__':unittest.main()
