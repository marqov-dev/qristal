import copy
import json
import unittest
from check import ROOT, verify, main


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / 'distribution/catalog.json').read_text())

    def test_retained_native_evidence(self):
        main()

    def test_rejects_promotion_and_identity_changes(self):
        for index, key, value in [(0,'access','public_registry'),(0,'identity','sha256:wrong'),
                                  (1,'access','public_registry'),(1,'identity','sha256:wrong')]:
            with self.subTest(index=index, key=key):
                data = copy.deepcopy(self.catalog)
                data['artifacts'][index][key] = value
                with self.assertRaises(ValueError):
                    verify(data)

    def test_rejects_unbound_or_modified_records(self):
        for change in ('missing', 'hash', 'hosted'):
            data = copy.deepcopy(self.catalog)
            if change == 'missing':
                del data['records'][data['artifacts'][0]['qualification']]
            elif change == 'hash':
                data['records'][next(iter(data['records']))] = '0' * 64
            else:
                data['hosted_available'] = True
            with self.assertRaises(ValueError):
                verify(data)
