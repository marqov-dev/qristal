import copy
import hashlib
import json
import unittest
from demo import analyze, core, schedule


def synthetic():
    records = []
    for item in schedule():
        p = core.forward(core.FIXTURES[item['fixture']][1],
                         **dict(a=item['options']['readout']['p10'],
                                b=item['options']['readout']['p01']))
        counts = {b: int(p[b]*core.SHOTS) for b in core.BITS}
        counts[max(p, key=p.get)] += core.SHOTS-sum(counts.values())
        records.append(dict(item, counts={b:n for b,n in counts.items() if n},
                            backend='aer',
                            program_sha256=hashlib.sha256(item['program'].encode()).hexdigest(),
                            options_sha256=hashlib.sha256(json.dumps(item['options'],sort_keys=True).encode()).hexdigest()))
    return dict(schema='qb-readout-drift-v1',records=records)


class DriftTests(unittest.TestCase):
    def test_schedule(self):
        items=schedule()
        self.assertEqual(len(items),40)
        self.assertEqual(len({i['options']['seed'] for i in items}),40)

    def test_analytic_limit_and_overcorrection(self):
        result=analyze(synthetic())
        for s in result['settings']:
            self.assertLess(s['mae']['fresh'],.001)
        last=result['settings'][-1]['mae']
        self.assertGreater(last['stale'],last['raw'])
        self.assertEqual(result['settings'][0]['mae']['fresh'],
                         result['settings'][0]['mae']['stale'])

    def test_binding(self):
        report=synthetic()
        report['records'][0]['options']=copy.deepcopy(report['records'][0]['options'])
        report['records'][0]['options']['seed']+=1
        with self.assertRaisesRegex(ValueError,'binding'):
            analyze(report)

    def test_corrupt_observation(self):
        report=synthetic()
        report['records'][0]['counts']={'11':core.SHOTS}
        with self.assertRaisesRegex(ValueError,'raw_model'):
            analyze(report)
