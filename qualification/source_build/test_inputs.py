import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare


class InputTests(unittest.TestCase):
    def test_inventory_detects_changed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a').write_text('one')
            before=prepare.inventory(root)
            (root/'a').write_text('two')
            self.assertNotEqual(before,prepare.inventory(root))

    def test_escaping_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):prepare.inventory(root)

    def test_private_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'private').mkdir(mode=0o700)
            with self.assertRaises(ValueError):prepare.inventory(root)

    def test_fixed_bootstrap_and_deadline(self):
        spec=importlib.util.spec_from_file_location('source_runner',Path(__file__).with_name('run.py'))
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        text=mod.bootstrap('https://example.invalid/input','a'*64).decode()
        self.assertIn('shutdown -h +60',text)
        self.assertIn('docker.io',text)
        self.assertNotIn('chmod -R',text)
        mod.lifecycle.SupervisorBase=mod.lifecycle.Supervisor
        with patch.object(mod.lifecycle.SupervisorBase,'initialize') as initialize:
            mod.SourceSupervisor.initialize('directory',{},b'input')
            self.assertEqual(initialize.call_args.kwargs,{'seconds':3600,'cleanup_seconds':300})


if __name__=='__main__':unittest.main()
