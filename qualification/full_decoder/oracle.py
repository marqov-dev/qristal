"""Exact, small classical CTC beam oracle; not a quantum execution result."""
from fractions import Fraction
from itertools import product
import math


def beam_probabilities(table, *, blank=0):
    """Collapse adjacent repetitions first, then remove blanks; enumerate <=4096 paths."""
    if not table or not table[0]:
        raise ValueError('empty_table')
    width = len(table[0])
    if type(blank) is not int or not 0 <= blank < width:
        raise ValueError('blank_index')
    # Bound enumeration before constructing any paths.
    if len(table) * math.log2(width) > 12:
        raise ValueError('path_limit')
    rows = []
    for row in table:
        if len(row) != width:
            raise ValueError('ragged_table')
        try:
            values = [Fraction(str(value)) for value in row]
        except (ValueError, ZeroDivisionError):
            raise ValueError('invalid_probability') from None
        if any(value < 0 or value > 1 for value in values) or sum(values) != 1:
            raise ValueError('invalid_probability')
        rows.append(values)
    beams = {}
    for path in product(range(width), repeat=len(rows)):
        probability = math.prod(rows[t][symbol] for t, symbol in enumerate(path))
        beam = tuple(symbol for t, symbol in enumerate(path)
                     if (t == 0 or symbol != path[t - 1]) and symbol != blank)
        beams[beam] = beams.get(beam, Fraction(0)) + probability
    return beams
