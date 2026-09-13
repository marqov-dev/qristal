import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from check import inspect


class SourceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'source.cpp').write_text('original\n')
        (self.root / '.gitignore').write_text('build/\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.commit = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def test_clean_receipt_is_source_only_and_deterministic(self):
        self.assertEqual(inspect(self.root, self.commit), inspect(self.root, self.commit))
        self.assertEqual(len(inspect(self.root, self.commit)['entries']), 2)

    def test_wrong_revision(self):
        with self.assertRaises(ValueError):
            inspect(self.root, '0' * 40)

    def test_assume_unchanged_does_not_hide_modified_bytes(self):
        self.git('update-index', '--assume-unchanged', 'source.cpp')
        (self.root / 'source.cpp').write_text('modified\n')
        with self.assertRaisesRegex(ValueError, 'working bytes'):
            inspect(self.root, self.commit)

    def test_ignored_build_inputs_rejected(self):
        (self.root / 'build').mkdir()
        (self.root / 'build' / 'old.so').write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            inspect(self.root, self.commit)

    def test_staged_change_rejected(self):
        (self.root / 'source.cpp').write_text('staged\n')
        self.git('add', '.')
        with self.assertRaisesRegex(ValueError, 'staged'):
            inspect(self.root, self.commit)

    def test_replaced_file_symlink_rejected(self):
        (self.root / 'source.cpp').unlink()
        (self.root / 'source.cpp').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'file type'):
            inspect(self.root, self.commit)

    def test_executable_bit_rejected(self):
        os.chmod(self.root / 'source.cpp', 0o755)
        with self.assertRaisesRegex(ValueError, 'mode mismatch'):
            inspect(self.root, self.commit)

    def test_materialized_submodule_and_dirty_child(self):
        child = self.root / 'sub'
        child.mkdir()
        subprocess.run(['git', '-C', str(child), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(child), 'config', 'user.name', 'Fixture'], check=True)
        subprocess.run(['git', '-C', str(child), 'config', 'user.email', 'fixture@example.invalid'], check=True)
        (child / 'child.cpp').write_text('child\n')
        subprocess.run(['git', '-C', str(child), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(child), 'commit', '-qm', 'child'], check=True)
        oid = subprocess.check_output(['git', '-C', str(child), 'rev-parse', 'HEAD'], text=True).strip()
        self.git('update-index', '--add', '--cacheinfo', '160000,' + oid + ',sub')
        self.git('commit', '-qm', 'materialized gitlink')
        commit = self.git('rev-parse', 'HEAD').strip()
        receipt = inspect(self.root, commit)
        self.assertEqual(receipt['entries'][-1]['submodule']['commit'], oid)
        self.git('config', 'diff.ignoreSubmodules', 'all')
        self.git('update-index', '--cacheinfo', '160000,' + self.commit + ',sub')
        with self.assertRaisesRegex(ValueError, 'staged'):
            inspect(self.root, commit)
        self.git('update-index', '--cacheinfo', '160000,' + oid + ',sub')
        (child / 'extra').write_text('undeclared')
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            inspect(self.root, commit)
        (child / 'extra').unlink()
        (child / 'child.cpp').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'working bytes'):
            inspect(self.root, commit)

    def test_source_symlink_scope(self):
        (self.root / 'link').symlink_to('source.cpp')
        self.git('add', '.')
        self.git('commit', '-qm', 'internal link')
        inspect(self.root, self.git('rev-parse', 'HEAD').strip())
        (self.root / 'link').unlink()
        (self.root / 'link').symlink_to('/etc/passwd')
        self.git('add', '.')
        self.git('commit', '-qm', 'external link')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            inspect(self.root, self.git('rev-parse', 'HEAD').strip())

    def test_parent_symlink_rejected(self):
        folder = self.root / 'nested'
        folder.mkdir()
        (folder / 'input').write_text('original')
        self.git('add', '.')
        self.git('commit', '-qm', 'nested file')
        commit = self.git('rev-parse', 'HEAD').strip()
        (folder / 'input').unlink()
        folder.rmdir()
        folder.symlink_to('/etc', target_is_directory=True)
        with self.assertRaises(ValueError):
            inspect(self.root, commit)

    def test_local_fsmonitor_is_disabled(self):
        hook = self.root / '.git' / 'forbidden-monitor'
        marker = self.root / '.git' / 'monitor-called'
        hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n')
        hook.chmod(0o755)
        self.git('config', 'core.fsmonitor', str(hook))
        inspect(self.root, self.commit)
        self.assertFalse(marker.exists())

    def test_submodule_must_be_materialized(self):
        self.git('update-index', '--add', '--cacheinfo', '160000,' + self.commit + ',sub')
        self.git('commit', '-qm', 'gitlink fixture')
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            inspect(self.root, self.git('rev-parse', 'HEAD').strip())


if __name__ == '__main__':
    unittest.main()
