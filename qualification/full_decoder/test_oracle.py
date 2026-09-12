import unittest
from fractions import Fraction
from oracle import beam_probabilities


class BeamOracleTests(unittest.TestCase):
    def test_historical_fixture(self):
        self.assertEqual(beam_probabilities([['.7', '.3'], ['.2', '.8']]),
                         {(): Fraction(14, 100), (1,): Fraction(86, 100)})

    def test_best_beam_is_not_best_path(self):
        # Most likely individual path is blank/blank (.36), but beam 'a' totals .64.
        self.assertEqual(beam_probabilities([['.6', '.4']] * 2),
                         {(): Fraction(36, 100), (1,): Fraction(64, 100)})

    def test_blank_separates_repeated_symbols(self):
        result = beam_probabilities([[0, 1], [1, 0], [0, 1]])
        self.assertEqual(result[(1, 1)], 1)
        self.assertEqual(sum(result.values()), 1)

    def test_repetitions_collapse(self):
        self.assertEqual(beam_probabilities([[0, 1]] * 3)[(1,)], 1)

    def test_multisymbol_mass(self):
        result = beam_probabilities([['.2', '.3', '.5']] * 3)
        self.assertEqual(sum(result.values()), 1)
        self.assertEqual(result[(1, 2, 1)], Fraction(45, 1000))

    def test_rejects_invalid_or_excessive_tables(self):
        for table in ([], [[]], [[1, 0], [1]], [[-1, 2]], [[.2, .2]],
                      [[float('nan'), 1]], [[.5, .5]] * 13):
            with self.subTest(table=table), self.assertRaises(ValueError):
                beam_probabilities(table)


if __name__ == '__main__':
    unittest.main()
