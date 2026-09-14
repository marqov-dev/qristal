import unittest
from wheel_linkage_guest import mappings_cover

class MappingTests(unittest.TestCase):
    def test_scipy_cannot_borrow_numpy_mapping_evidence(self):
        numpy=['/env/numpy.libs/'+name for name in ('libopenblas.so','libgfortran.so','libquadmath.so')]
        self.assertTrue(mappings_cover('numpy',numpy))
        self.assertFalse(mappings_cover('scipy',numpy))
        scipy=['/env/scipy.libs/'+name for name in ('libscipy_openblas.so','libgfortran.so','libquadmath.so')]
        self.assertTrue(mappings_cover('scipy',numpy+scipy))
