import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('core_output', Path(__file__).with_name('output.py'))
output = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output)


class OutputTests(unittest.TestCase):
    def fixture(self, root, success):
        roots = {name: root / name for name in (output.SUCCESS_ROOTS if success else {'logs'})}
        for path in roots.values():
            path.mkdir()
        (roots['logs'] / 'build.log').write_bytes(b'full log')
        report = {'native_passed': success, 'stages': {'build': {'log_sha256': output.digest(b'full log')}}}
        if success:
            (roots['install-core'] / 'lib').mkdir()
            (roots['install-core'] / 'lib/libcircuits.so.1.8.1').write_bytes(b'library')
            (roots['install-xacc'] / 'plugins').mkdir()
            (roots['install-xacc'] / 'plugins/libcircuits.so.1.8.1').symlink_to('/work/install-core/lib/libcircuits.so.1.8.1')
            (roots['antlr'] / 'antlr4_python3_runtime-4.9.2-py3-none-any.whl').write_bytes(b'wheel')
            (roots['consumer'] / 'core.cpp').write_bytes(b'source')
            (roots['consumer-output'] / 'core').write_bytes(b'consumer')
            report['plugin_normalization'] = output.normalize(root)
            report['retained_files'] = {'antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl': output.digest(b'wheel'),
                                        'consumer/core.cpp': output.digest(b'source'), 'consumer-output/core': output.digest(b'consumer')}
        else:
            report['error'] = 'build failed'
        return report, roots

    def test_success_normalize_and_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, True)
            link = root / 'install-xacc/plugins/libcircuits.so.1.8.1'
            self.assertEqual(str(link.readlink()), '../../install-core/lib/libcircuits.so.1.8.1')
            self.assertEqual(link.read_bytes(), b'library')
            archive = root / 'success.tar.gz'
            identity = output.pack(archive, report, roots)
            self.assertTrue(output.verify(archive, identity, report)['verified'])
            self.assertFalse(report['plugin_normalization']['installed_consumer_replayed'])

    def test_failure_logs_only_and_report_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, False)
            archive = root / 'failure.tar.gz'
            identity = output.pack(archive, report, roots)
            self.assertFalse(output.verify(archive, identity, report)['native_passed'])
            with self.assertRaises(ValueError):
                output.verify(archive, identity, dict(report, error='different'))
            with self.assertRaises(ValueError):
                output.pack(root / 'bad.tar.gz', report, dict(roots, **{'install-core': root}))

    def test_unlisted_secret_log_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, False)
            (roots['logs'] / 'output-put.conf').write_text('do not retain')
            with self.assertRaises(ValueError):
                output.pack(root / 'bad.tar.gz', report, roots)

    def test_unknown_absolute_link_rejected_without_partial_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, True)
            link = roots['install-xacc'] / 'plugins/libcircuits.so.1.8.1'
            link.unlink()
            link.symlink_to('/work/install-core/lib/libcircuits.so.1.8.1')
            (roots['install-xacc'] / 'plugins/zunknown').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                output.normalize(root)
            self.assertTrue(str(link.readlink()).startswith('/'))

    def test_dangling_and_escaping_links_rejected(self):
        for target in ('missing', '../../../escape'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                report, roots = self.fixture(root, True)
                (roots['install-core'] / 'bad').symlink_to(target)
                archive = root / 'bad.tar.gz'
                with self.assertRaises(ValueError):
                    identity = output.pack(archive, report, roots)
                    output.verify(archive, identity, report)

    def test_log_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, False)
            (roots['logs'] / 'build.log').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                output.pack(root / 'bad.tar.gz', report, roots)

    def test_consumer_identity_and_output_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, True)
            with patch.object(output, 'MAX_BYTES', 10), self.assertRaises(ValueError):
                output.pack(root / 'too-big.tar.gz', report, roots)
            (roots['consumer-output'] / 'core').write_bytes(b'other binary')
            with self.assertRaises(ValueError):
                output.pack(root / 'different.tar.gz', report, roots)

    def test_cyclic_link_and_archive_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, roots = self.fixture(root, True)
            path = root / 'existing.tar.gz'
            path.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):
                output.pack(path, report, roots)
            self.assertEqual(path.read_bytes(), b'keep')
            (roots['install-core'] / 'a').symlink_to('b')
            (roots['install-core'] / 'b').symlink_to('a')
            with self.assertRaises(ValueError):
                output.pack(root / 'cycle.tar.gz', report, roots)


if __name__ == '__main__':
    unittest.main()
