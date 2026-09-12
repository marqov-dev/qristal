import random
import unittest
from study import multinomial, wilson


class SamplingTests(unittest.TestCase):
    def test_deterministic_boundaries(self):
        self.assertEqual(multinomial(random.Random(1),{"00":1.0,"10":0.0}),{"00":16384})
        self.assertEqual(multinomial(random.Random(1),{"00":0.0,"10":1.0}),{"10":16384})

    def test_independent_sampling_moments(self):
        rng=random.Random(9)
        values=[multinomial(rng,{"00":.25,"10":.75}).get("00",0) for _ in range(1000)]
        self.assertLess(abs(sum(values)/1000-4096),10)
        self.assertGreater(len(set(values)),50)

    def test_wilson_boundaries(self):
        self.assertAlmostEqual(wilson(0,1000)[0],0)
        self.assertAlmostEqual(wilson(1000,1000)[1],1)
        low,high=wilson(950,1000)
        self.assertLess(low,.95)
        self.assertGreater(high,.95)
