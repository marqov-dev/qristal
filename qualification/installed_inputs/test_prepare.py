import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('installed_prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
a = prepare.archive


class PreparationTests(unittest.TestCase):
    def fixture(self, root, collision=False):
        roots = {name: root / name for name in ('install-xacc', 'consumer', 'consumer-output', 'logs')}
        for path in roots.values():
            path.mkdir()
        (roots['install-xacc'] / 'lib.so').write_bytes(b'library')
        (roots['install-xacc'] / 'alias.so').symlink_to('lib.so')
        (roots['consumer-output'] / 'acz').write_bytes(b'consumer')
        (roots['logs'] / 'build.log').write_bytes(b'log')
        installed = {'lib.so': a.digest(b'library')}
        if collision:
            (roots['install-xacc'] / 'LIB.so').write_bytes(b'upper')
            installed['LIB.so'] = a.digest(b'upper')
        report = {'native_passed': True, 'installed_files': len(installed),
                  'installed_manifest_sha256': a.digest(json.dumps(installed, sort_keys=True).encode()),
                  'consumer_sha256': a.digest(b'consumer'),
                  'stages': {'build': {'log_sha256': a.digest(b'log')}}}
        path = root / 'archive.tar.gz'
        identity = a.pack(path, report, roots)
        return path, dict(report, output_artifact=identity)

    def test_roundtrip_preserves_modes_links_and_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            original = path.read_bytes()
            result = prepare.prepare(path, report, root / 'out')
            self.assertTrue(result['verified'])
            self.assertFalse(result['executed'])
            self.assertEqual(path.read_bytes(), original)
            receipt = json.loads((root / 'out/staging.json').read_text())
            prepare.verify_tree(root / 'out/tree', receipt['entries'])
            (root / 'out/tree/install-xacc/lib.so').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'staged file'):
                prepare.verify_tree(root / 'out/tree', receipt['entries'])

    def test_tampered_archive_creates_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            path.write_bytes(path.read_bytes() + b'tampered')
            with self.assertRaises(ValueError):
                prepare.prepare(path, report, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_existing_and_linked_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            (root / 'out').mkdir()
            with self.assertRaises(ValueError): prepare.prepare(path, report, root / 'out')
            (root / 'link').symlink_to('missing')
            with self.assertRaises(ValueError): prepare.prepare(path, report, root / 'link')

    def test_failure_report_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            report['native_passed'] = False
            with self.assertRaisesRegex(ValueError, 'native success'):
                prepare.prepare(path, report, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_wrong_identity_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            report['output_artifact']['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'archive hash'):
                prepare.prepare(path, report, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_archive_transport_does_not_unpack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path, report = self.fixture(root)
            result = prepare.prepare(path, report, root / 'out', archive_only=True)
            self.assertEqual(result['materialization'], 'archive-only')
            self.assertFalse((root / 'out/tree').exists())
            self.assertEqual((root / 'out/archive.tar.gz').read_bytes(), path.read_bytes())
            prepare.prepare(root / 'out/archive.tar.gz', report, root / 'replay')
            self.assertTrue((root / 'replay/tree/install-xacc/alias.so').is_symlink())

    def test_case_sensitive_archive_on_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probe = root / 'CaseProbe'; probe.touch()
            insensitive = (root / 'caseprobe').exists(); probe.unlink()
            if insensitive:
                # Construct a Linux-like case-distinct archive in memory from
                # an ordinary fixture; production verification must still pass.
                path, report = self.fixture(root)
                import io, tarfile
                with tarfile.open(path) as tar:
                    members = [(m, tar.extractfile(m).read() if m.isfile() else None) for m in tar]
                receipt = json.loads(next(data for m,data in members if m.name == 'receipt.json'))
                extra = 'install-xacc/LIB.so'
                receipt['entries'][extra] = {'type':'file','mode':0o644,'size':5,'sha256':a.digest(b'upper')}
                report.pop('output_artifact')
                report['installed_files'] = 2
                report['installed_manifest_sha256'] = a.digest(json.dumps({'lib.so':a.digest(b'library'),'LIB.so':a.digest(b'upper')},sort_keys=True).encode())
                raw = a.canonical(report)
                receipt['report_sha256'] = a.digest(raw)
                receipt['entries']['report.json'].update(size=len(raw),sha256=a.digest(raw))
                with tarfile.open(path,'w:gz') as tar:
                    for m,data in members:
                        if m.name == 'report.json': data=raw
                        if m.name == 'receipt.json': data=a.canonical(receipt)
                        if data is not None: m.size=len(data)
                        tar.addfile(m,io.BytesIO(data) if data is not None else None)
                    m=tarfile.TarInfo(extra);m.mode=0o644;m.size=5;tar.addfile(m,io.BytesIO(b'upper'))
                report['output_artifact'] = {'bytes':path.stat().st_size,'sha256':a.digest(path.read_bytes()),'receipt_sha256':a.digest(a.canonical(receipt)),'report_sha256':a.digest(raw)}
                with self.assertRaisesRegex(ValueError,'case-sensitive filesystem'):
                    prepare.prepare(path,report,root/'out')
                self.assertFalse((root/'out').exists())
            else:
                path, report = self.fixture(root, collision=True)
                prepare.prepare(path,report,root/'out')
                self.assertEqual((root/'out/tree/install-xacc/LIB.so').read_bytes(),b'upper')
