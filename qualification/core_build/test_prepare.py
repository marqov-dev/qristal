import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        source = self.inputs / 'qristal-core/cmake'
        source.mkdir(parents=True)
        self.original = b'# fixture\n' * 87 + prepare.OLD + b'# retained install behavior\n'
        (source / 'dependencies.cmake').write_bytes(self.original)
        self.source = source / 'dependencies.cmake'
        receipt = {'source': {'commit': prepare.SOURCE_COMMIT, 'tree': 'fixture', 'entries': [
            {'path': 'cmake/dependencies.cmake', 'mode': '100644', 'git_blob': 'fixture',
             'sha256': prepare.sha(self.original), 'bytes': len(self.original)}]}}
        raw = json.dumps(receipt).encode()
        (self.inputs / 'core-source.json').write_bytes(raw)
        self.addCleanup(patch.stopall)
        patch.object(prepare, 'RECEIPT_SHA256', prepare.sha(raw)).start()
        patch.object(prepare, 'DEPENDENCIES_SHA256', prepare.sha(self.original)).start()

    def test_only_dependency_location_changes_and_receipt_is_not_build(self):
        output = self.root / 'result'
        result = prepare.prepare(self.inputs, output)
        self.assertEqual(self.source.read_bytes(), self.original)
        changed = (output / 'qristal-core/cmake/dependencies.cmake').read_bytes()
        self.assertEqual(changed, self.original.replace(prepare.OLD, prepare.NEW))
        self.assertEqual(result['derived_dependency_sha256'], prepare.sha(changed))
        self.assertFalse(result['configured'])
        self.assertFalse(result['native_qualified'])
        effective_raw = (output / 'effective-source.json').read_bytes()
        self.assertEqual(result['effective_manifest_sha256'], prepare.sha(effective_raw))
        effective = json.loads(effective_raw)
        self.assertNotIn('commit', effective)
        self.assertNotIn('git_blob', effective['entries'][0])
        prepare.source_export.verify_tree(output / 'qristal-core', effective)
        (output / 'qristal-core/cmake/dependencies.cmake').write_bytes(b'changed afterward')
        with self.assertRaises(ValueError):
            prepare.source_export.verify_tree(output / 'qristal-core', effective)

    def test_modified_source_rejected_before_output(self):
        self.source.write_bytes(self.original + b'extra')
        output = self.root / 'result'
        with self.assertRaises(ValueError):
            prepare.prepare(self.inputs, output)
        self.assertFalse(output.exists())

    def test_extra_source_rejected(self):
        (self.inputs / 'qristal-core/undeclared').write_bytes(b'old binary')
        with self.assertRaises(ValueError):
            prepare.prepare(self.inputs, self.root / 'result')

    def test_receipt_tampering_rejected(self):
        (self.inputs / 'core-source.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'unapproved'):
            prepare.prepare(self.inputs, self.root / 'result')

    def test_nested_or_existing_output_rejected(self):
        for output in (self.inputs / 'result', self.inputs):
            with self.assertRaises(ValueError):
                prepare.prepare(self.inputs, output)

    def test_replaced_source_symlink_does_not_read_external_bytes(self):
        self.source.unlink()
        self.source.symlink_to('/outside-not-a-source-fixture')
        with self.assertRaises(ValueError):
            prepare.prepare(self.inputs, self.root / 'result')

    def test_nonmatching_dependency_hash_rejected(self):
        with self.assertRaises(ValueError):
            prepare.transform(self.original + b'other change')


if __name__ == '__main__':
    unittest.main()
