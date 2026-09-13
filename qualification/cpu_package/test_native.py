import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import guest
import pack_native
import run_native
import stage


class NativeTests(unittest.TestCase):
    def test_bootstrap_preserves_modes_and_fixed_deadline(self):
        script = run_native.bootstrap('https://example.test/artifact', 'a' * 64)
        self.assertEqual(subprocess.run(['bash', '-n'], input=script, capture_output=True).returncode, 0)
        self.assertIn(b'shutdown -h +20', script)
        self.assertIn(b'timeout 240', script)
        self.assertNotIn(b'chmod -R', script)
        self.assertNotIn(b'install-toolchain', script)
        for url in ("https://example.test/'", 'https://example.test/\n'):
            with self.assertRaises(ValueError):
                run_native.bootstrap(url, 'a' * 64)

    def test_report_recovers_with_existing_protocol(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gpu_package'))
        import console
        data = {'kind':'qb-cpu-oci-native-v1','native_passed':True,'tests':{'image':'fixture'}}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            guest.emit(data)
        recovered, _, _ = console.recover(output.getvalue())
        self.assertEqual(recovered, data)

    def test_archive_contains_only_context_and_named_harness(self):
        import tarfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            (source / 'fixture').write_text('public fixture')
            context = root / 'context'
            with patch.dict(stage.INPUTS, {'fixture':'opt/fixture'}, clear=True):
                stage.stage(source, stage.capture(source), context)
            artifact = root / 'artifact'
            pack_native.pack(context, artifact)
            with tarfile.open(artifact / 'cpu.tar.gz') as archive:
                roots = {p.name.split('/')[0] for p in archive.getmembers()}
            self.assertEqual(roots, {'context','stage.py','guest.py','qristal','manifest.json'})
            record = json.loads((artifact / 'archive.json').read_text())
            self.assertEqual(record['sha256'], stage.sha(artifact / 'cpu.tar.gz'))
            with self.assertRaises(ValueError):
                pack_native.pack(context, context / 'bad')
