import importlib.util
from pathlib import Path
import tempfile
import subprocess
import unittest
import test_check

spec = importlib.util.spec_from_file_location('source_export', Path(__file__).with_name('export.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    setUp = test_check.SourceGateTests.setUp
    git = test_check.SourceGateTests.git

    def output(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / 'source'

    def test_export_ignores_working_changes_and_extras(self):
        (self.root / 'source.cpp').write_text('dirty')
        (self.root / 'untracked').write_text('not an input')
        output = self.output()
        receipt = module.export_tree(self.root, self.commit, output)
        self.assertEqual((output / 'source.cpp').read_text(), 'original\n')
        self.assertFalse((output / 'untracked').exists())
        module.verify_tree(output, receipt)
        (output / 'source.cpp').write_text('changed')
        with self.assertRaises(ValueError):
            module.verify_tree(output, receipt)

    def test_extra_exported_file_rejected(self):
        output = self.output()
        receipt = module.export_tree(self.root, self.commit, output)
        (output / 'extra').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            module.verify_tree(output, receipt)

    def test_existing_destination_rejected(self):
        output = self.output()
        output.mkdir()
        with self.assertRaises(FileExistsError):
            module.export_tree(self.root, self.commit, output)

    def test_unsafe_receipt_path_rejected(self):
        output = self.output()
        receipt = module.export_tree(self.root, self.commit, output)
        receipt['entries'][0]['path'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            module.verify_tree(output, receipt)

    def test_replaced_root_symlink_rejected(self):
        output = self.output()
        receipt = module.export_tree(self.root, self.commit, output)
        moved = output.with_name('moved')
        output.rename(moved)
        output.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'real directory'):
            module.verify_tree(output, receipt)

    def test_export_uses_gitlink_commit_not_child_head(self):
        child = self.root / 'sub'
        child.mkdir()
        def cg(*args):
            return subprocess.check_output(['git', '-C', str(child), *args], text=True).strip()
        cg('init', '-q')
        cg('config', 'user.name', 'Fixture')
        cg('config', 'user.email', 'fixture@example.invalid')
        (child / 'value').write_text('locked')
        cg('add', '.')
        cg('commit', '-qm', 'locked')
        locked = cg('rev-parse', 'HEAD')
        self.git('update-index', '--add', '--cacheinfo', '160000,' + locked + ',sub')
        self.git('commit', '-qm', 'gitlink')
        (child / 'value').write_text('later')
        cg('add', '.')
        cg('commit', '-qm', 'later')
        output = self.output()
        receipt = module.export_tree(self.root, self.git('rev-parse', 'HEAD').strip(), output)
        self.assertEqual((output / 'sub' / 'value').read_text(), 'locked')
        module.verify_tree(output, receipt)

    def test_export_internal_symlink(self):
        (self.root / 'link').symlink_to('source.cpp')
        self.git('add', '.')
        self.git('commit', '-qm', 'link')
        output = self.output()
        receipt = module.export_tree(self.root, self.git('rev-parse', 'HEAD').strip(), output)
        module.verify_tree(output, receipt)
        self.assertTrue((output / 'link').is_symlink())

    def test_export_escaping_symlink_rejected(self):
        (self.root / 'link').symlink_to('/etc/passwd')
        self.git('add', '.')
        self.git('commit', '-qm', 'link')
        with self.assertRaisesRegex(ValueError, 'escaping'):
            module.export_tree(self.root, self.git('rev-parse', 'HEAD').strip(), self.output())

class RetainedExportTests(unittest.TestCase):
    def test_retained_receipt_hashes_and_counts(self):
        import gzip
        import hashlib
        import json
        root = Path(__file__).resolve().parents[1] / 'evidence/2026-09-13-pristine-sources'
        summary = json.loads((root / 'summary.json').read_text())
        def totals(tree):
            files = size = children = 0
            for entry in tree['entries']:
                if 'submodule' in entry:
                    f, b, c = totals(entry['submodule'])
                    files += f; size += b; children += c + 1
                else:
                    files += 1; size += entry['bytes']
            return files, size, children
        for item in summary['components']:
            stored = (root / item['receipt']).read_bytes()
            raw = gzip.decompress(stored)
            self.assertEqual(hashlib.sha256(stored).hexdigest(), item['stored_sha256'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['receipt_sha256'])
            tree = json.loads(raw)['source']
            self.assertEqual(tree['commit'], item['commit'])
            self.assertEqual(tree['tree'], item['tree'])
            self.assertEqual(totals(tree), (item['files'], item['bytes'], item['submodules']))


if __name__ == '__main__':
    unittest.main()
