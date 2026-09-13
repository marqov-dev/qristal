import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recipe


class RecipeTests(unittest.TestCase):
    def test_retained_recipe_hashes(self):
        root = Path(__file__).resolve().parent
        receipt = json.loads((root / 'inspection.json').read_text())
        self.assertFalse(receipt['built'])
        for name, digest in receipt['recipe_sha256'].items():
            self.assertEqual(recipe.sha((root / name).read_bytes()), digest)

    def wheel(self, root, *, native=False, altered=False):
        files = {
            'antlr4/__init__.py': b'# fixture only',
            'antlr4_python3_runtime-4.9.2.data/scripts/pygrun': b'#!python\n',
            recipe.DIST + '/METADATA': b'Name: antlr4-python3-runtime\nVersion: 4.9.2\nLicense: BSD\nRequires-Dist: typing ; python_version < "3.5"\n',
            recipe.DIST + '/WHEEL': ('Root-Is-Purelib: ' + ('false' if native else 'true') + '\nTag: py3-none-any\n').encode(),
        }
        record = io.StringIO()
        writer = csv.writer(record)
        for name, data in files.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
            writer.writerow([name, 'sha256=' + digest, len(data)])
        writer.writerow([recipe.DIST + '/RECORD', '', ''])
        files[recipe.DIST + '/RECORD'] = record.getvalue().encode()
        if altered:
            files['antlr4/__init__.py'] = b'changed'
        path = root / 'antlr4_python3_runtime-4.9.2-py3-none-any.whl'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return path

    def test_synthetic_metadata_and_record(self):
        with tempfile.TemporaryDirectory() as root:
            result = recipe.verify(self.wheel(Path(root)))
            self.assertTrue(result['metadata_verified'])
            self.assertFalse(result['native_runtime_tested'])

    def test_native_flag_and_tamper_rejected(self):
        for options in ({'native': True}, {'altered': True}):
            with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
                recipe.verify(self.wheel(Path(root), **options))

    def test_unsafe_paths(self):
        for name in ('/absolute', '../escape', 'a/../escape', './a', 'a\\b'):
            with self.assertRaises(ValueError):
                recipe.safe(name)


if __name__ == '__main__':
    unittest.main()
