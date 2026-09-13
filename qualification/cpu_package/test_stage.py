import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import stage


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.lib = self.workspace / 'lib'
        self.lib.mkdir()
        (self.lib / 'native.so.1').write_bytes(b'ELF-fixture')
        (self.lib / 'native.so').symlink_to('native.so.1')
        self.script = self.workspace / 'runtime.py'
        self.script.write_text('print("fixture")\n')
        self.script.chmod(0o755)
        self.mapping = patch.dict(stage.INPUTS, {'lib':'work/lib', 'runtime.py':'opt/runtime.py'}, clear=True)
        self.mapping.start()
        self.addCleanup(self.mapping.stop)
        self.output = self.root / 'context'

    def test_capture_stage_verify_preserves_links_and_permissions(self):
        receipt = stage.capture(self.workspace)
        stage.stage(self.workspace, receipt, self.output)
        stage.verify_context(self.output)
        self.assertEqual((self.output / 'payload/work/lib/native.so').readlink(), Path('native.so.1'))
        self.assertEqual((self.output / 'payload/opt/runtime.py').stat().st_mode & 0o777, 0o755)
        self.assertEqual(receipt['provenance'], 'observed_installed_bytes_not_verified_build_origin')
        with self.assertRaises(ValueError):
            stage.stage(self.workspace, receipt, self.output)

    def test_input_changes_rejected_before_output_created(self):
        receipt = stage.capture(self.workspace)
        (self.lib / 'native.so.1').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            stage.stage(self.workspace, receipt, self.output)
        self.assertFalse(self.output.exists())

    def test_forged_destination_rejected(self):
        receipt = stage.capture(self.workspace)
        receipt['inputs']['lib']['destination'] = '../../escape'
        with self.assertRaises(ValueError):
            stage.stage(self.workspace, receipt, self.output)
        self.assertFalse(self.output.exists())

    def test_context_changes_rejected(self):
        stage.stage(self.workspace, stage.capture(self.workspace), self.output)
        (self.output / 'payload/opt/runtime.py').write_text('changed')
        with self.assertRaises(ValueError):
            stage.verify_context(self.output)

    def test_extra_context_and_metadata_changes_rejected(self):
        stage.stage(self.workspace, stage.capture(self.workspace), self.output)
        extra = self.output / 'unexpected'
        extra.write_text('not allowlisted')
        with self.assertRaises(ValueError):
            stage.verify_context(self.output)
        extra.unlink()
        (self.output / 'Dockerfile').write_text('changed')
        with self.assertRaises(ValueError):
            stage.verify_context(self.output)

    def test_external_link_and_special_file_rejected(self):
        link = self.lib / 'external'
        link.symlink_to('../runtime.py')
        with self.assertRaises(ValueError):
            stage.capture(self.workspace)
        link.unlink()
        import os
        os.mkfifo(self.lib / 'pipe')
        with self.assertRaises(ValueError):
            stage.capture(self.workspace)

    def test_change_during_copy_rejected(self):
        receipt = stage.capture(self.workspace)
        original = stage.shutil.copytree
        def damaged_copy(src, dst, **kwargs):
            original(src, dst, **kwargs)
            (dst / 'native.so.1').write_bytes(b'changed during copy')
        with patch.object(stage.shutil, 'copytree', side_effect=damaged_copy):
            with self.assertRaises(ValueError):
                stage.stage(self.workspace, receipt, self.output)
        self.assertFalse((self.output / 'context.json').exists())

    def test_bell_overlay_is_bound_to_final_payload(self):
        checks = self.workspace / 'checks'
        checks.mkdir()
        (checks / 'bell.qasm').write_text('old')
        self.script.write_text('new')
        with patch.dict(stage.INPUTS, {'checks':'checks', 'runtime.py':'checks/bell.qasm'}, clear=True):
            receipt = stage.capture(self.workspace)
            stage.stage(self.workspace, receipt, self.output)
        stage.verify_context(self.output)
        self.assertEqual((self.output / 'payload/checks/bell.qasm').read_text(), 'new')

    def test_output_inside_input_rejected(self):
        with self.assertRaises(ValueError):
            stage.stage(self.workspace, stage.capture(self.workspace), self.lib / 'recursive')
        self.assertFalse((self.lib / 'recursive').exists())

    def test_private_umask_does_not_hide_generated_container_parents(self):
        receipt = stage.capture(self.workspace)
        previous = os.umask(0o077)
        try:
            stage.stage(self.workspace, receipt, self.output)
        finally:
            os.umask(previous)
        for name in ('payload', 'payload/work', 'payload/opt'):
            self.assertEqual((self.output / name).stat().st_mode & 0o777, 0o755)
        stage.verify_context(self.output)

    def test_unreadable_installed_file_rejected(self):
        self.script.chmod(0o700)
        with self.assertRaises(ValueError):
            stage.stage(self.workspace, stage.capture(self.workspace), self.output)
        self.assertFalse((self.output / 'context.json').exists())

    def test_absolute_container_link_uses_declared_destination(self):
        (self.lib / 'native.so').unlink()
        (self.lib / 'native.so').symlink_to('/work/lib/native.so.1')
        stage.stage(self.workspace, stage.capture(self.workspace), self.output)
        stage.verify_context(self.output)
        self.assertEqual(str((self.output / 'payload/work/lib/native.so').readlink()), '/work/lib/native.so.1')

    def test_missing_absolute_target_and_cycles_rejected(self):
        link = self.lib / 'native.so'
        link.unlink()
        link.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            stage.capture(self.workspace)
        link.unlink()
        link.symlink_to('native.so')
        with self.assertRaises(ValueError):
            stage.capture(self.workspace)

    def test_overlay_never_writes_through_destination_symlink(self):
        checks = self.workspace / 'checks'
        checks.mkdir()
        sentinel = self.root / 'sentinel'
        sentinel.write_text('untouched')
        (checks / 'bell.qasm').symlink_to(sentinel)
        with patch.dict(stage.INPUTS, {'checks':'checks', 'runtime.py':'checks/bell.qasm'}, clear=True):
            stage.stage(self.workspace, stage.capture(self.workspace), self.output)
        self.assertEqual(sentinel.read_text(), 'untouched')
        self.assertFalse((self.output / 'payload/checks/bell.qasm').is_symlink())
        stage.verify_context(self.output)

    def test_parent_traversal_link_rejected(self):
        link = self.lib / 'native.so'
        link.unlink()
        link.symlink_to('native.so.1/../native.so.1')
        with self.assertRaises(ValueError):
            stage.capture(self.workspace)
